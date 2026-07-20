from __future__ import annotations

import json
import os
import random
import sys
from typing import Any

from neo4j import GraphDatabase

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grafo_visual import salvar  # noqa: E402
from crud_pipeline import (  # noqa: E402
    NOW,
    PROJECT_DEFS,
    SEED,
    _dump_json,
    banner,
    gen_id,
    iso,
    score_band,
    show,
    step,
)

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

NEO4J_URI = os.getenv("MT_NEO4J_URI", "bolt://localhost:7688")
NEO4J_USER = os.getenv("MT_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("MT_NEO4J_PASSWORD", "modeltrace123")
NEO4J_DATABASE = os.getenv("MT_NEO4J_DATABASE", "neo4j")

NODE_LABELS = ["Organization", "Project", "Model", "ModelVersion",
               "Entity", "Prediction", "Feature", "Outcome"]

# Tamanho do pool de entidades por projeto vem do proprio PROJECT_DEFS
# (campo n_entities), definido em crud_pipeline.py.
DEFAULT_ENTITIES_PER_PROJECT = 30
OUTCOMES = ["tp", "fp", "tn", "fn", "pending"]


# ===========================================================================
# Geracao do dataset ficticio (mesmo tema dos 3 projetos do crud_pipeline)
# ===========================================================================


def build_dataset() -> dict[str, Any]:
    """Gera organization/projects/models/versions/entities/predictions/features
    prontos para virar nos e relacionamentos no Neo4j. Reaproveita PROJECT_DEFS
    e gen_id() do crud_pipeline.py para os IDs baterem com o dominio do Mongo."""
    random.seed(SEED)

    organization = {"id": "org_ufu_gi_ops", "label": "UFU GI Decision Ops Lab"}
    projects: list[dict] = []
    models: list[dict] = []
    versions: list[dict] = []
    entities: list[dict] = []
    predictions: list[dict] = []
    features_seen: dict[str, str] = {}
    outcome_counts = {o: 0 for o in OUTCOMES}
    risk_factor_agg: dict[tuple[str, str], dict[str, float]] = {}

    for pdef in PROJECT_DEFS:
        projects.append({
            "id": pdef["id"], "label": pdef["name"], "domain": pdef["domain"],
            "entity_type": pdef["entity_type"],
        })

        project_entities = []
        n_ent = pdef.get("n_entities", DEFAULT_ENTITIES_PER_PROJECT)
        prefix = pdef.get("entity_prefix", pdef["entity_type"])
        for i in range(n_ent):
            ent = {
                "id": gen_id("gentity", pdef["id"], str(i)),
                "label": f"{prefix}#{i:03d}",
                "entity_type": pdef["entity_type"], "domain": pdef["domain"],
                "project_id": pdef["id"],
            }
            entities.append(ent)
            project_entities.append(ent)

        for mdef in pdef["models"]:
            model_id = gen_id("model", pdef["id"], mdef["slug"])
            models.append({
                "id": model_id, "label": mdef["name"], "algorithm": mdef["algo"],
                "project_id": pdef["id"],
            })
            for f in mdef["features"]:
                features_seen.setdefault(f, pdef["domain"])

            version_ids = {}
            for vname, vstatus in (("v1", "deprecated"), ("v2", "production")):
                vid = gen_id("version", model_id, vname)
                version_ids[vname] = vid
                versions.append({
                    "id": vid, "label": f"{mdef['name']} · {vname}",
                    "version": vname, "status": vstatus, "model_id": model_id,
                })

            for ent in project_entities:
                for k in range(random.randint(1, 2)):
                    vname = random.choices(["v1", "v2"], weights=[0.25, 0.75], k=1)[0]
                    version_id = version_ids[vname]
                    score = max(0.0, min(1.0, random.gauss(pdef["base_mean"], 0.2)))
                    above = score >= pdef["threshold"]
                    label_value = pdef["positive"] if above else pdef["negative"]
                    top = random.sample(mdef["features"], min(3, len(mdef["features"])))
                    explanations = [
                        {"feature": fn, "impact": round(0.05 + random.random() * 0.3 * score, 4), "rank": rank}
                        for rank, fn in enumerate(top, start=1)
                    ]

                    if random.random() < 0.7:
                        target = max(0.03, min(0.97, 0.45 * pdef["base_mean"] + 0.55 * score))
                        observed = 1 if random.random() < target else 0
                        outcome = ("tp" if above and observed else "fp" if above and not observed
                                   else "fn" if not above and observed else "tn")
                    else:
                        outcome = "pending"
                    outcome_counts[outcome] += 1

                    pred_id = gen_id("gpred", version_id, ent["id"], str(k))
                    predictions.append({
                        "id": pred_id, "label": f"{label_value} · {round(score, 3)}",
                        "score": round(score, 4), "score_band": score_band(score),
                        "label_value": label_value, "version_id": version_id,
                        "entity_id": ent["id"], "outcome": outcome,
                        "explanations": explanations,
                    })

                    for exp in explanations:
                        agg = risk_factor_agg.setdefault((ent["id"], exp["feature"]),
                                                          {"impact_sum": 0.0, "n": 0})
                        agg["impact_sum"] += exp["impact"]
                        agg["n"] += 1

    features = [{"id": f"feat::{name}", "label": name, "domain": dom, "name": name}
                for name, dom in features_seen.items()]
    outcomes = [{"id": f"outcome::{o}", "label": o.upper(), "count": outcome_counts[o]}
                for o in OUTCOMES]
    risk_factors = [
        {"entity_id": eid, "feature": feat, "avg_impact": round(v["impact_sum"] / v["n"], 4), "n": v["n"]}
        for (eid, feat), v in risk_factor_agg.items()
    ]

    return {
        "organization": organization, "projects": projects, "models": models,
        "versions": versions, "entities": entities, "predictions": predictions,
        "features": features, "outcomes": outcomes, "risk_factors": risk_factors,
    }


# ===========================================================================
# Repositorio: grafo (Neo4j) + GDS
# ===========================================================================


class GraphRepository:
    """Camada de acesso ao Neo4j + Graph Data Science para o grafo de conhecimento."""

    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def connect(self) -> None:
        self.driver.verify_connectivity()
        version = self.run("CALL dbms.components() YIELD name, versions "
                            "RETURN name, versions[0] AS version LIMIT 1")[0]
        gds_version = self.run("RETURN gds.version() AS v")[0]["v"]
        step(f"Neo4j conectado: {NEO4J_URI} ({version['name']} {version['version']})")
        step(f"Graph Data Science (GDS) disponivel: v{gds_version}")

    def run(self, query: str, **params: Any) -> list[dict]:
        with self.driver.session(database=NEO4J_DATABASE) as session:
            return [r.data() for r in session.run(query, **params)]

    def _drop_graph_if_exists(self, name: str) -> None:
        self.run("CALL gds.graph.drop($name, false) YIELD graphName RETURN graphName", name=name)

    # =======================================================================
    # 1) CONSTRUIR o grafo: nos + relacionamentos (UNWIND + MERGE em lote)
    # =======================================================================
    def build_graph(self, ds: dict) -> None:
        self.run("MATCH (n) DETACH DELETE n")
        for label in NODE_LABELS:
            self.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")
        step("Grafo limpo (DETACH DELETE) e constraints de unicidade criadas (8 labels).")

        self.run("UNWIND $rows AS row MERGE (n:Organization {id: row.id}) SET n.label = row.label",
                  rows=[ds["organization"]])
        self.run("UNWIND $rows AS row MERGE (n:Project {id: row.id}) "
                  "SET n.label = row.label, n.domain = row.domain, n.entity_type = row.entity_type",
                  rows=ds["projects"])
        self.run("UNWIND $rows AS row MERGE (n:Model {id: row.id}) "
                  "SET n.label = row.label, n.algorithm = row.algorithm",
                  rows=ds["models"])
        self.run("UNWIND $rows AS row MERGE (n:ModelVersion {id: row.id}) "
                  "SET n.label = row.label, n.version = row.version, n.status = row.status",
                  rows=ds["versions"])
        self.run("UNWIND $rows AS row MERGE (n:Entity {id: row.id}) "
                  "SET n.label = row.label, n.entity_type = row.entity_type, n.domain = row.domain",
                  rows=ds["entities"])
        self.run("UNWIND $rows AS row MERGE (n:Prediction {id: row.id}) "
                  "SET n.label = row.label, n.score = row.score, n.score_band = row.score_band, "
                  "n.label_value = row.label_value, n.outcome = row.outcome",
                  rows=ds["predictions"])
        self.run("UNWIND $rows AS row MERGE (n:Feature {id: row.id}) "
                  "SET n.label = row.label, n.domain = row.domain",
                  rows=ds["features"])
        self.run("UNWIND $rows AS row MERGE (n:Outcome {id: row.id}) "
                  "SET n.label = row.label, n.count = row.count",
                  rows=ds["outcomes"])
        step(f"Nos: 1 organization, {len(ds['projects'])} projects, {len(ds['models'])} models, "
             f"{len(ds['versions'])} versions, {len(ds['entities'])} entities, "
             f"{len(ds['predictions'])} predictions, {len(ds['features'])} features, "
             f"{len(ds['outcomes'])} outcomes.")

        self.run("MATCH (o:Organization {id: $oid}) UNWIND $rows AS row "
                  "MATCH (p:Project {id: row.id}) MERGE (o)-[:OWNS]->(p)",
                  oid=ds["organization"]["id"], rows=ds["projects"])
        self.run("UNWIND $rows AS row MATCH (p:Project {id: row.project_id}), (m:Model {id: row.id}) "
                  "MERGE (p)-[:HAS_MODEL]->(m)", rows=ds["models"])
        self.run("UNWIND $rows AS row MATCH (m:Model {id: row.model_id}), (v:ModelVersion {id: row.id}) "
                  "MERGE (m)-[:HAS_VERSION]->(v)", rows=ds["versions"])
        self.run("UNWIND $rows AS row MATCH (v:ModelVersion {id: row.version_id}), (pr:Prediction {id: row.id}) "
                  "MERGE (v)-[:PRODUCED]->(pr)", rows=ds["predictions"])
        self.run("UNWIND $rows AS row MATCH (pr:Prediction {id: row.id}), (e:Entity {id: row.entity_id}) "
                  "MERGE (pr)-[:FOR_ENTITY]->(e)", rows=ds["predictions"])
        self.run("UNWIND $rows AS row MATCH (pr:Prediction {id: row.id}), (o:Outcome {id: 'outcome::' + row.outcome}) "
                  "MERGE (pr)-[:CLASSIFIED_AS]->(o)", rows=ds["predictions"])

        driven_by_rows = [
            {"pred_id": p["id"], "feature": exp["feature"], "impact": exp["impact"], "rank": exp["rank"]}
            for p in ds["predictions"] for exp in p["explanations"]
        ]
        self.run("UNWIND $rows AS row MATCH (pr:Prediction {id: row.pred_id}), (f:Feature {id: 'feat::' + row.feature}) "
                  "MERGE (pr)-[d:DRIVEN_BY]->(f) SET d.impact = row.impact, d.rank = row.rank",
                  rows=driven_by_rows)
        self.run("UNWIND $rows AS row MATCH (e:Entity {id: row.entity_id}), (f:Feature {id: 'feat::' + row.feature}) "
                  "MERGE (e)-[r:RISK_FACTOR]->(f) SET r.weight = row.avg_impact, r.n = row.n",
                  rows=ds["risk_factors"])
        step(f"Relacionamentos: OWNS, HAS_MODEL, HAS_VERSION, PRODUCED, FOR_ENTITY, CLASSIFIED_AS, "
             f"DRIVEN_BY ({len(driven_by_rows)}), RISK_FACTOR ({len(ds['risk_factors'])}).")

    # =======================================================================
    # 2) GDS 1/3 - Node Similarity: "casos parecidos" entre entidades
    # =======================================================================
    def run_gds_similar_cases(self) -> dict:
        self._drop_graph_if_exists("entity-feature")
        self.run("CALL gds.graph.project($name, ['Entity','Feature'], 'RISK_FACTOR')", name="entity-feature")
        res = self.run(
            "CALL gds.nodeSimilarity.write($name, {writeRelationshipType: 'SIMILAR_TO', "
            "writeProperty: 'score', topK: 5, similarityCutoff: 0.1}) "
            "YIELD nodesCompared, relationshipsWritten, similarityDistribution",
            name="entity-feature",
        )[0]
        self._drop_graph_if_exists("entity-feature")
        return res

    # =======================================================================
    # 3) GDS 2/3 - Louvain: comunidades (clusters) de padrao de risco
    # =======================================================================
    def run_gds_communities(self) -> dict:
        self._drop_graph_if_exists("entity-similarity")
        self.run("CALL gds.graph.project($name, 'Entity', "
                  "{SIMILAR_TO: {orientation: 'UNDIRECTED', properties: 'score'}})",
                  name="entity-similarity")
        res = self.run(
            "CALL gds.louvain.write($name, {writeProperty: 'community_id', "
            "relationshipWeightProperty: 'score'}) YIELD communityCount, modularity",
            name="entity-similarity",
        )[0]
        self._drop_graph_if_exists("entity-similarity")
        return res

    # =======================================================================
    # 4) GDS 3/3 - PageRank: influencia estrutural no grafo inteiro
    # =======================================================================
    def run_gds_influence(self) -> dict:
        self._drop_graph_if_exists("full-graph")
        self.run("CALL gds.graph.project($name, " + json.dumps(NODE_LABELS) + ", '*')", name="full-graph")
        res = self.run(
            "CALL gds.pageRank.write($name, {writeProperty: 'pagerank'}) "
            "YIELD nodePropertiesWritten, ranIterations, didConverge",
            name="full-graph",
        )[0]
        self._drop_graph_if_exists("full-graph")
        return res

    # =======================================================================
    # 5) Exportar grafo + resultados GDS (JSON pronto para a viz 2D/3D)
    # =======================================================================
    def fetch_export(self) -> dict:
        nodes = self.run(
            "MATCH (n) RETURN n.id AS id, coalesce(n.label, n.id) AS label, "
            "labels(n)[0] AS type, properties(n) AS props"
        )
        links = self.run(
            "MATCH (a)-[r]->(b) RETURN a.id AS source, b.id AS target, type(r) AS type, "
            "properties(r) AS props"
        )
        return {"nodes": nodes, "links": links}

    def export_and_write(self, sim_stats: dict, louvain_stats: dict, pagerank_stats: dict) -> dict:
        graph = self.fetch_export()
        top_similarity = self.run(
            "MATCH (a:Entity)-[r:SIMILAR_TO]->(b:Entity) "
            "RETURN a.id AS a_id, a.label AS a_label, b.id AS b_id, b.label AS b_label, "
            "round(r.score, 4) AS score ORDER BY r.score DESC LIMIT 15"
        )
        top_pagerank = self.run(
            "MATCH (n) WHERE n.pagerank IS NOT NULL RETURN n.id AS id, "
            "coalesce(n.label, n.id) AS label, labels(n)[0] AS type, "
            "round(n.pagerank, 4) AS pagerank ORDER BY n.pagerank DESC LIMIT 15"
        )
        communities = self.run(
            "MATCH (e:Entity) WHERE e.community_id IS NOT NULL "
            "RETURN e.community_id AS community, count(*) AS size, "
            "collect(e.id)[0..6] AS sample_ids, collect(e.label)[0..6] AS sample "
            "ORDER BY size DESC"
        )

        payload = {
            "generated_at": iso(NOW),
            "stats": {
                "nodes": len(graph["nodes"]), "edges": len(graph["links"]),
                "communities": louvain_stats.get("communityCount"),
                "modularity": round(louvain_stats.get("modularity", 0), 4),
                "similarity_pairs_written": sim_stats.get("relationshipsWritten"),
                "pagerank_iterations": pagerank_stats.get("ranIterations"),
            },
            "nodes": graph["nodes"],
            "links": graph["links"],
            "top_similarity": top_similarity,
            "top_pagerank": top_pagerank,
            "communities": communities,
        }

        _dump_json("graph_export.json", payload)
        _dump_json("graph_gds_top_similarity.json", top_similarity)
        _dump_json("graph_gds_top_pagerank.json", top_pagerank)
        _dump_json("graph_gds_communities.json", communities)

        # A visualizacao fica inteira em grafo_visual.py (biblioteca Constelario).
        destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grafo.html")
        salvar(payload, destino)
        step(f"grafo.html gerado ({payload['stats']['nodes']} nos, "
             f"{payload['stats']['edges']} arestas).")
        return payload


# ===========================================================================
# Orquestracao
# ===========================================================================


def main() -> None:
    repo = GraphRepository()

    banner("FASE 0 - CONEXAO (Neo4j + GDS)")
    repo.connect()

    banner("FASE 1 - GERAR DATASET FICTICIO (mesmo tema dos 3 projetos do crud_pipeline)")
    ds = build_dataset()
    step(f"Gerado: {len(ds['entities'])} entities, {len(ds['predictions'])} predictions, "
         f"{len(ds['features'])} features, {len(ds['risk_factors'])} pares entity-feature agregados.")

    banner("FASE 2 - CONSTRUIR O GRAFO (nos + relacionamentos)")
    repo.build_graph(ds)

    banner("FASE 3 - GDS 1/3: gds.nodeSimilarity.write (Radar de Casos Similares)")
    sim_stats = repo.run_gds_similar_cases()
    show(sim_stats)

    banner("FASE 4 - GDS 2/3: gds.louvain.write (comunidades de padrao de risco)")
    louvain_stats = repo.run_gds_communities()
    show(louvain_stats)

    banner("FASE 5 - GDS 3/3: gds.pageRank.write (influencia estrutural)")
    pagerank_stats = repo.run_gds_influence()
    show(pagerank_stats)

    banner("FASE 6 - EXPORTAR RESULTADOS + ATUALIZAR graph_visualizacao.html")
    payload = repo.export_and_write(sim_stats, louvain_stats, pagerank_stats)
    step(f"Grafo final: {payload['stats']['nodes']} nos, {payload['stats']['edges']} arestas, "
         f"{payload['stats']['communities']} comunidades (modularidade={payload['stats']['modularity']}).")

    print("\n  Top 5 casos mais similares (gds.nodeSimilarity):")
    for row in payload["top_similarity"][:5]:
        print(f"    - {row['a_label']:<14} <-> {row['b_label']:<14}  score={row['score']}")

    print("\n  Top 5 nos mais influentes (gds.pageRank):")
    for row in payload["top_pagerank"][:5]:
        print(f"    - [{row['type']:<12}] {row['label']:<28} pagerank={row['pagerank']}")

    print("\n  Comunidades de padrao de risco (gds.louvain):")
    for row in payload["communities"][:8]:
        print(f"    - comunidade {row['community']:<3} {row['size']:>3} entidades  ex: {row['sample']}")

    banner("SUMARIO FINAL - CONTAGEM POR TIPO DE NO")
    for label in NODE_LABELS:
        cnt = repo.run(f"MATCH (n:{label}) RETURN count(n) AS c")[0]["c"]
        print(f"  {label:14} {cnt:>5}")
    print("\nPipeline de grafo concluido com sucesso.")


if __name__ == "__main__":
    main()
