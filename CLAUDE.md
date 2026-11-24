# Leitor de Planta

Você lê a planta baixa de um projeto de arquitetura e entrega uma página animada: passa o mouse (ou toca, no celular) num ambiente, ele se enche de cor varrendo da esquerda para a direita, o resto da planta recua e o nome aparece. A pessoa dona desta pasta é quem projetou: ela decide nome, cor e o que entra.

## Primeira vez nesta pasta

Crie o ambiente das ferramentas e instale o que elas usam (leva uns 2 minutos):

```
python3 -m venv .venv && .venv/bin/pip install -r ferramentas/requisitos.txt
```

Se o Mac pedir para instalar as ferramentas de linha de comando, a pessoa aprova e você roda de novo. Daqui para frente, todo comando usa `.venv/bin/python`.

## Passo a passo

1. **A planta.** Procure em `planta/` (PDF, PNG ou JPG; uma planta por pavimento). Se estiver vazia, peça para a pessoa arrastar o arquivo para lá. Pergunte o nome do projeto, se ela ainda não disse.
2. **Preparar.** `.venv/bin/python ferramentas/preparar.py planta/ARQUIVO`. Sai a imagem com grade (`.grade.png`) e, se o PDF tiver texto de verdade, o `.textos.json` com cada palavra e a posição dela em pixels.
3. **Ler.** Abra o `.grade.png` e olhe a planta inteira. Escreva `planta/NOME.comodos.json`:
   ```json
   {"comodos": [
     {"nome": "Sala", "numero": 11, "m2": 24.5, "setor": "social", "retangulos": [[x0, y0, x1, y1]]},
     {"nome": "Cozinha", "retangulos": [[x0, y0, x1, y1], [x0, y0, x1, y1]]}
   ]}
   ```
   - Um ambiente por cômodo. O nome vem da legenda ou do texto da planta; se a planta não tiver texto, deduza pela mobília (cama é quarto, bacia sanitária é banheiro, fogão é cozinha) e avise que deduziu.
   - Coordenadas em pixels da imagem, lidas na grade (ou no `.textos.json`, que é exato). O retângulo encosta na face de dentro das paredes e ignora a mobília. Armário embutido, marcenaria e bancada fazem parte do cômodo: a borda vai até a parede atrás deles.
   - Porta: a borda atravessa o vão em linha reta, na linha da parede, sem contornar a folha nem o arco. A área de abertura (o arco) é do cômodo para onde a porta abre; nunca do cômodo do outro lado da parede.
   - Corredor e circulação que a legenda não nomeia não se dividem entre os cômodos vizinhos. Se a passagem é de um ambiente (o corredor da suíte, que leva ao closet e ao banho), entra inteira nesse ambiente; se é de todos, vira um ambiente "Circulação". Cada cômodo para na parede dele, mesmo com o corredor logo depois.
   - Escada não é ambiente: entra inteira no ambiente em que está inserida (o hall, a sala, o estúdio). Nunca crie "Escada" como ambiente nem deixe a escada fora de todos os recortes.
   - Todo piso dentro da casa tem dono: não sobra área branca entre ambientes. Área aberta perto de escada, bancada ou banco é do ambiente em volta.
   - Hall e corredor comprido: só a faixa entre as paredes dele, sem entrar em outro ambiente.
   - `numero` quando a planta numera os ambientes (o número do selo na planta).
   - Cômodo em L leva mais de um retângulo.
   - Parede curva ou canto arredondado: marque o retângulo que cobre o cômodo. O `ajustar.py` completa até a curva (bolsão) ou apara o canto que passa dela (corte) sozinho. Arco tracejado de porta não conta como parede. Ambientes integrados (estar e jantar, cozinha aberta) se dividem em linha reta, no alinhamento da parede mais próxima.
   - `m2` só quando a planta mostra. Jardim e área sem piso ficam de fora, a não ser que a pessoa peça.
   - `setor` de cada cômodo: `social`, `intimo`, `servico`, `molhado`, `circulacao` ou `externo`.
4. **Encostar nas paredes.** `.venv/bin/python ferramentas/ajustar.py planta/ARQUIVO.png planta/NOME.comodos.json`. Abra o `NOME.comodos.conferir.png` e confira cada cômodo:
   - só linha reta;
   - o recorte não entra no vizinho nem sai da casa (faltar um pedacinho é melhor que vazar);
   - nenhum cômodo pela metade.
   O `ajustar.py` também imprime **avisos** da conferência automática: escada separada como ambiente, área de piso dentro da casa que ficou sem dono, parede atravessando um recorte (corredor ou vizinho entrou junto), cômodos sobrepostos, número de ambiente fora do recorte ou dentro do recorte errado, área longe do m² da planta. Corrija até zerar os avisos ou saber explicar cada um. Depois de três voltas sem acertar um cômodo, mostre e pergunte.
5. **Mostrar a leitura.** Mostre o `conferir.png` e a lista de nomes, e pergunte se estão certos. Quem projetou sabe o nome de cada ambiente.
6. **Animar.** `.venv/bin/python ferramentas/montar.py planta/NOME.comodos.ajustado.json saida/NOME --titulo "Nome do projeto"`. Ela sai na Paleta 1.
7. **Escolher a cor, no painel.** Rode **em segundo plano** `.venv/bin/python ferramentas/cores.py saida/NOME`. O navegador abre a página com um painel ao lado, e ela escolhe vendo a planta: a paleta (cinco paletas coloridas), pintar por ambiente ou por setor, as réguas de temperatura, intensidade e claridade, a cor de cada ambiente ou setor e as cores da página (fundo, texto, borda). Salvar grava na página; Concluir grava e encerra o comando, e aí você sabe que ela terminou. O painel não vai para a página final.
   - Se ela preferir escolher por imagem, `.venv/bin/python ferramentas/amostras.py planta/NOME.comodos.ajustado.json [--modo setor]` gera a folha com a planta pintada em cada paleta. As cores do escritório entram com `montar.py ... --cores "#hex,#hex,#hex"`.
8. **Entregar.** A pasta `saida/NOME` é o site inteiro: abre direto no navegador e sobe em qualquer hospedagem de site estático. Para mandar ao cliente, a pessoa escolhe onde publicar.

## Ajustes que ela pode pedir

- "O banheiro está pegando o corredor": mexa no retângulo daquele cômodo e rode os passos 4 e 6 (o passo 6 refaz a página: depois abra o painel de novo, passo 7).
- Trocar nome, juntar ou separar ambientes: edite o `comodos.json` e rode os passos 4, 6 e 7.
- Trocar a cor: só o passo 7.
- Outro pavimento: repita do passo 2 com a outra planta, em `saida/NOME-pavimento`.

## Combinados

- A planta original não muda. Tudo que você gera fica em `planta/` e `saida/`.
- Nada sobe para a internet sem a pessoa pedir.
- Destaque de ambiente é cor sólida com borda. Nunca contorno tracejado com película transparente.
