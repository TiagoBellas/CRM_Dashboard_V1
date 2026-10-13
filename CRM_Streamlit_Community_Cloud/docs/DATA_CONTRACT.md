# Contrato de resultados e preservacao semântica

## O que este contrato resolve

O app apresenta valores já avaliados. A separacao evita que uma implementacao Python
substitua indevidamente DAX por `len`, `count`, `sum`, `nunique` ou um filtro simples.
Ela não recupera as medidas ainda desconhecidas nem prova a equivalencia do backend.

Um snapshot representa UMA página em UM contexto completo de filtros e acesso,
para UMA release do modelo e um instante de carga. Cada cartao, serie e tabela deve
ser avaliado no contexto proprio do visual, incluindo excecoes de interacao como NoFilter.

Dois utilizadores so podem partilhar um snapshot quando os resultados autorizados
forem realmente equivalentes para esse contexto. Um filtro sobre um agregado global
não e substituto de executar o modelo com a RLS correta.

## Campos de cabecalho

| Campo | Tipo | Conteudo |
|---|---|---|
| schema_version | inteiro | 1 |
| snapshot_id | string | ID unico do snapshot na release |
| release_id | string | Release igual a app.expected_release |
| source_sha256 | string | Hash do PBIX original em metadata/pbi_manifest.json |
| page_id / page_title | string | ID e titulo originais da página |
| quarter | string | Ex.: Q4-2026; representa o contexto explicito |
| context_id / context_label | string | Identificador e descricao legivel do contexto completo |
| is_default | booleano | Exatamente um por página autorizada; calculado segundo a regra original |
| as_of | string ISO-8601 | Instante de carga com fuso, não horario do browser |
| filter_context | objeto JSON | Estado completo de filtros, nivel de relatorio/página/visual e contexto de acesso |
| certification | objeto | Atestados externos e referência da evidencia |
| authorized_viewer_key | string | Obrigatório apenas no upload reference; identidade vinculada ao pacote |
| cards / charts / tables / notes | listas | Resultados já avaliados |

O ficheiro `examples/snapshot.pending.json` e um modelo inicial BLOQUEADO. O estado
PENDING impede a exibicao como resultado real. Os nomes/IDs conhecidos derivam
dos vinculos do PBIX; os valores não foram preenchidos com estimativas.

## Homologação

Para dados reais, o contrato exige status CERTIFIED e scope values_in_fixed_context,
alem de semantic_version, security_version, approved_by e evidence_ref preenchidos.
Exige também atestados booleanos de value_parity, filter_context_parity,
access_policy_parity e presentation_reviewed.

Esses campos sao declaracoes de governanca: o software verifica a estrutura, a
consistencia e a presenca dos atestados, mas NÃO executa uma prova automatica de
homologação no Power BI. Uma pessoa poder alterar um JSON não torna os valores homologados.
Não marque a demo como CERTIFIED para contornar os bloqueios.

O aceite deve comparar o mesmo modelo/snapshot de dados e os mesmos utilizadores:
seleções simples e vazias, limites de trimestre, Q1 versus Q4 anterior, filtros
ocultos, totais distintos das somas visiveis, BLANK, denominadores zero e regras RLS.
A multisselecao arbitraria de trimestres não e implementada nesta interface.

## Cartoes

Cada cartao informa id, source_visual_id, measure, label, value e formatted_value.
O source_visual_id deve pertencer a página e measure deve constar dos vinculos
extraidos daquele visual. value pode ser número finito ou null. formatted_value
e o TEXTO final produzido/revisto na camada semântica, incluindo percentagem e BLANK.
O Streamlit não recalcula percentagens nem escolhe uma politica para denominadores zero.

```json
{
  "id": "deals_qoq",
  "source_visual_id": "22bb00a877b1667e72b5",
  "measure": "_QuarterComparison[Q. Deals QoQ %]",
  "label": "Deals QoQ %",
  "value": null,
  "formatted_value": ""
}
```

Este exemplo ilustra um BLANK, não um valor observado do PBIX.

## Graficos

O renderer admite series bar e line, eixos y/y2 e empilhamento group/stack. Cada serie
contem x, y e display_y com o mesmo comprimento. y possui números finitos/null;
display_y preserva o texto de tooltip da origem. Numeros percentuais devem usar
fracao (0.25 para 25%) quando o eixo for configurado como percent.

Não ha normalizacao automatica de shares nem cálculo de totais no grafico.
A camada de origem tem de fornecer shares corretos no contexto de cada visual.
HTML, JavaScript, objetos Plotly arbitrarios ou especificacoes Deneb não sao executados.
Os IDs dos visuais permitem rastreabilidade, não garantem identidade visual ou interativa.

## Tabelas e matrizes

Uma tabela contem id, source_visual_id, title, columns e rows. A ordem das linhas,
as hierarquias achatadas, os subtotais e o total geral sao fornecidos na origem.
Não existe pivot/groupby/soma na interface. Para preservar formatos, exporte celulas
formatadas como strings; BLANK pode ser string vazia ou null conforme o contrato aprovado.
O exemplo de display não implementa expand/collapse das matrizes do Power BI.

## Databricks: armazenamento

As colunas do indice SQL devem coincidir exatamente com os campos homonimos do JSON.
O app confere essa correspondencia antes de renderizar. `payload_sha256` e o SHA-256
da string `payload_json` EXATA em UTF-8, não de outro JSON semanticamente equivalente.
`snapshot_id` e `release_id` não devem ser reutilizados para conteudos diferentes.

O SQL de schema não contem uma consulta inventada de Pipeline. Falta recuperar e
traduzir as medidas ou exportar resultados corretamente avaliados pelo modelo original.
Esse pipeline precisa ser implementado/homologado pela equipa de dados; não e simulado aqui.

Valide um ficheiro depois de obter a aprovacao real:

```bash
python scripts/validate_snapshot.py private_data/meu_snapshot.json --release crm-v5-2026-10-13-r1
```

O script fornece o hash dos bytes que validou. Se o formato do JSON mudar depois,
recalcule o hash. Os dados reais e evidencias que contenham informação sensivel
ficam em armazenamento controlado, não no GitHub do aplicativo.

## Escopo funcional conhecido

As notas do PBIX documentam Current pelo trimestre escolhido, Previous completo
e mesmo trimestre LY completo, sem ajuste por dias decorridos. O default e o
trimestre mais recente existente nos dados segundo o contexto original, não today().
A interface apenas mostra as janelas; não resolve a granularidade da contagem.

O filtro global oculto Show Row - Closed This Year Or Blank, Terminal Snapshot,
relacionamentos, RLS e contextos de medida continuam requisitos do backend.
As convencoes de BLANK, a multisselecao, os totais e os visuais especiais não foram
inferidos a partir dos nomes de campos. O PBIX original continua sendo a referência.
