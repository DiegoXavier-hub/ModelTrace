# ModelTrace

> Plataforma de auditoria, observabilidade e governança para decisões de modelos de Machine Learning.

O **ModelTrace** é uma plataforma web criada para registrar, auditar e monitorar decisões tomadas por modelos de Machine Learning em produção. A proposta não é treinar modelos dentro do sistema, mas acompanhar o que eles decidem depois que já estão rodando em algum pipeline, API, sistema interno ou processo automatizado.

Cada predição enviada ao ModelTrace vira um evento rastreável: com dados de entrada, score, threshold, versão do modelo, explicações, decisão tomada, contexto da execução e, quando disponível, o resultado real observado depois.

Em outras palavras: o modelo decide em outro lugar. O ModelTrace guarda a responsabilidade da decisão.

---

## Por que esse projeto existe?

Modelos de Machine Learning são usados para apoiar decisões cada vez mais importantes: risco de evasão acadêmica, fraude, churn, crédito, priorização de atendimento, detecção de anomalias, recomendação de ações e muitos outros cenários.

O problema é que, depois de uma decisão ser tomada, muitas equipes não conseguem responder perguntas simples:

- Qual versão do modelo fez essa predição?
- Quais dados foram usados?
- Qual era o score?
- Qual threshold estava ativo naquele momento?
- Por que essa entidade foi classificada como risco alto?
- A decisão se confirmou depois?
- O modelo piorou com o tempo?
- Houve mudança na distribuição dos dados?
- Uma nova versão realmente melhorou ou só pareceu melhor no treino?
- Existe diferença de comportamento entre grupos?

O **ModelTrace** foi criado para responder essas perguntas de forma organizada, auditável e escalável.

---

## Entrega de valor

O valor principal do ModelTrace é transformar predições soltas em histórico confiável de decisão.

Ele ajuda equipes técnicas e de negócio a entenderem não apenas **o que o modelo previu**, mas também **como, quando, por qual versão e com qual consequência** aquela decisão foi tomada.

### Para cientistas de dados

O sistema permite acompanhar modelos depois do treinamento, comparando versões, monitorando performance real, detectando drift e analisando feedbacks posteriores. Isso reduz o risco de confiar apenas em métricas offline.

### Para analistas de negócio

A plataforma facilita a investigação de decisões específicas. Um analista pode abrir uma predição, ver o score, entender os principais fatores envolvidos, consultar o histórico e registrar anotações sobre a ação tomada.

### Para gestores e auditores

O ModelTrace oferece rastreabilidade. Cada evento importante fica registrado: ingestão de predição, feedback, alteração de threshold, criação de modelo, mudança de versão, alerta gerado e resolução de incidente.

### Para equipes de produto e engenharia

A API permite integrar modelos existentes sem reescrever o pipeline. Basta enviar as predições para o ModelTrace e deixar que o sistema cuide da organização, consulta, métricas, alertas e auditoria.

---

## Como funciona

O fluxo principal é simples:

```txt
Modelo externo gera uma predição
        ↓
A aplicação envia o resultado para a API do ModelTrace
        ↓
O sistema valida e registra a decisão no banco NoSQL
        ↓
Workers processam métricas, alertas e drift
        ↓
O front-end mostra dashboards, histórico e auditoria
        ↓
Quando o resultado real chega, o feedback é registrado
        ↓
A performance real do modelo é atualizada
