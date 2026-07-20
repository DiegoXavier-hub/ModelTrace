# -*- coding: utf-8 -*-
"""Visualizacao do grafo de conhecimento (biblioteca Constelario).

Unico arquivo do projeto que fala com a Constelario. Entra o resultado do
Neo4j + GDS (nos, arestas e rankings); sai um HTML interativo 2D/3D.
Nao ha aqui nenhuma logica de banco, de dataset ou de interface -- so grafo.

Uso:
    from grafo_visual import salvar
    salvar(payload, "grafo.html")
"""
from __future__ import annotations

from typing import Any

from constelario import Graph, Theme

# Aparencia por label do Neo4j: cor, icone, ornamento do medalhao e anel do
# layout radial (0 = centro). A ordem dos aneis desenha a hierarquia do dominio.
TIPOS = {
    "Organization": dict(label="Organizacao", color="#f2c766", icon="crown",
                         tier="keystone", ring=0),
    "Project":      dict(label="Projeto", color="#8b7bd8", icon="folder",
                         tier="notable", ring=1),
    "Model":        dict(label="Modelo", color="#5b8fc7", icon="cpu",
                         tier="notable", ring=2),
    "ModelVersion": dict(label="Versao de modelo", color="#7fb3d5",
                         icon="git-branch", ring=2.6),
    "Feature":      dict(label="Feature", color="#c2564f", icon="crosshair",
                         tier="notable", ring=3.5),
    "Outcome":      dict(label="Resultado", color="#e08a3c", icon="check-circle",
                         tier="notable", ring=3.5),
    "Entity":       dict(label="Entidade", color="#4a9c8c", icon="user", ring=4.8),
    # Predicoes sao a maior massa de nos: nascem desligadas na legenda e, no
    # layout Espiral/Globo, formam o halo externo.
    "Prediction":   dict(label="Predicao", color="#a98a54", icon="activity",
                         ring=6.2, hidden=True),
}

# Propriedades tecnicas que nao interessam no painel de inspecao.
PROPS_OCULTAS = ("id", "label", "entity_id", "project_id", "model_id", "version_id")


def construir(payload: dict) -> Graph:
    """Monta o objeto Graph a partir do payload exportado do Neo4j + GDS."""
    stats = payload.get("stats", {})
    g = Graph(
        title="ModelTrace",
        subtitle="Grafo de Conhecimento - Neo4j GDS",
        theme=Theme.relicario(),
        generated_at=payload.get("generated_at", ""),
    )

    for nome, estilo in TIPOS.items():
        g.add_type(nome, **estilo)

    for no in payload["nodes"]:
        props = dict(no.get("props") or {})
        g.add_node(no["id"], no.get("label") or no["id"], no["type"],
                   props=props, community=props.get("community_id"))

    for aresta in payload["links"]:
        g.add_edge(aresta["source"], aresta["target"],
                   type=aresta.get("type", ""), props=aresta.get("props") or {})

    # SIMILAR_TO e a aresta que a funcionalidade entrega (casos parecidos):
    # ganha destaque, espessura pelo score e um ranking proprio no inspetor.
    g.edge_style("SIMILAR_TO", color="#f2c766", width=1.6, opacity=0.6)
    g.set_edge_weight("score", min_width=0.6, max_width=4.0)
    g.inspector_ranking("SIMILAR_TO", title="Casos mais similares", score_prop="score")

    g.add_color_mode("domain", "Dominio", prop="domain")
    g.hide_props(*PROPS_OCULTAS)

    _paineis(g, payload)
    _estatisticas(g, stats)
    return g


def _paineis(g: Graph, payload: dict) -> None:
    """Os tres resultados do GDS viram paineis clicaveis na barra lateral."""
    g.add_panel(
        "Casos mais similares",
        [(f"{r['a_label']} <-> {r['b_label']}", r["score"], r["a_id"])
         for r in payload.get("top_similarity", [])[:10]],
        hint="gds.nodeSimilarity",
    )
    g.add_panel(
        "Nos mais influentes",
        [(f"[{TIPOS.get(r['type'], {}).get('label', r['type'])}] {r['label']}",
          r["pagerank"], r["id"])
         for r in payload.get("top_pagerank", [])[:10]],
        hint="gds.pageRank",
    )
    g.add_panel(
        "Comunidades de risco",
        [(f"Comunidade {c['community']} ({', '.join(c.get('sample', [])[:3])})",
          c["size"], (c.get("sample_ids") or [None])[0])
         for c in payload.get("communities", [])[:10]],
        hint="gds.louvain",
    )


def _estatisticas(g: Graph, stats: dict) -> None:
    """Numeros do GDS na caixa de estatisticas (a contagem de comunidades ja
    aparece nativamente, entao aqui vao so os numeros que faltam)."""
    for rotulo, chave in (("modularidade", "modularity"),
                          ("pares similares", "similarity_pairs_written"),
                          ("iteracoes pageRank", "pagerank_iterations")):
        valor = stats.get(chave)
        if valor is not None:
            g.add_stat(rotulo, valor)


def salvar(payload: dict, destino: str) -> str:
    """Gera o HTML interativo e devolve o caminho absoluto do arquivo."""
    return construir(payload).save(destino)


def main() -> None:
    """Regera o HTML a partir do ultimo export salvo em logs/."""
    import json
    import os

    raiz = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(raiz, "logs", "graph_export.json"), encoding="utf-8") as f:
        payload = json.load(f)
    print(salvar(payload, os.path.join(raiz, "grafo.html")))


if __name__ == "__main__":
    main()
