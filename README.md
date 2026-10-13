# NutriScan

Aplicativo e API em Python para acompanhamento de dieta, leitura de foto de tabelas nutricionais (fichas técnicas), consulta por código de barras (EAN-13) e verificação dos limites de rotulagem frontal da ANVISA (RDC 429/2020 e IN 75/2020). Inclui projeto Android nativo em Kotlin com build automático de APK no GitHub Actions.

## Funcionalidades

### 1. Minha Dieta (Controle de Limite Diário)
Painel diário com barra de progresso para meta de calorias (kcal) e macronutrientes (carboidratos, proteínas, gorduras totais e sódio). Suporta cálculo automático pela fórmula de Mifflin-St Jeor a partir do peso, altura, idade e objetivo (emagrecimento, manutenção ou ganho de massa), além de diário de refeições com registro por café da manhã, almoço, lanche e jantar.

![Painel de Dieta Diária no NutriScan](docs/screenshots/nutriscan_dieta.png)

### 2. Leitor de Foto da Ficha Técnica (Tabela Nutricional)
Permite tirar foto da tabela nutricional com a câmera do celular ou carregar imagem do rótulo. O extrator identifica porção-base, valor energético, carboidratos, proteínas, gorduras totais, gorduras saturadas, fibras e sódio, calculando os valores proporcionais exatos para a quantidade consumida (em gramas ou ml) e o impacto percentual na meta diária.

![Leitor de Foto da Tabela Nutricional](docs/screenshots/nutriscan_foto_ficha.png)

### 3. Código de Barras e Alertas ANVISA
Consulta a base aberta [Open Food Facts](https://world.openfoodfacts.org/) para obter dados nutricionais por código EAN-13, classifica pelo grau de processamento NOVA (1 a 4) e Nutri-Score (A a E), e aplica as regras da ANVISA para os selos de advertência frontal:

- **ALTO EM AÇÚCAR**: `>= 15 g` em sólidos ou `>= 7,5 g` em líquidos por 100g/100ml.
- **ALTO EM GORDURA SATURADA**: `>= 6 g` em sólidos ou `>= 3 g` em líquidos por 100g/100ml.
- **ALTO EM SÓDIO**: `>= 600 mg` em sólidos ou `>= 300 mg` em líquidos por 100g/100ml.

![Consulta de produto no NutriScan](docs/screenshots/nutriscan_produto.png)

### 4. Versão Mobile e Aplicativo Android (.APK)
Interface responsiva com barra inferior de navegação e suporte a PWA (Progressive Web App com `manifest.json` e `sw.js`). A pasta `android/` contém um projeto nativo em Kotlin/WebView com permissões de câmera integradas para tirar fotos de rótulos diretamente no celular.

<p align="center">
  <img src="docs/screenshots/nutriscan_mobile_android.png" alt="NutriScan no Celular Android" width="340" />
</p>

## Como baixar o APK para Android

O fluxo do GitHub Actions (`.github/workflows/android-apk.yml`) compila o APK debug automaticamente em cada push para a branch `main`.

1. Acesse a aba **Actions** ou **Releases** no repositório [Glawther/NutriScan](https://github.com/Glawther/NutriScan).
2. Baixe o artefato `NutriScan-Android-debug` (ou o arquivo `app-debug.apk`).
3. Instale diretamente no celular Android (habilite a instalação de fontes confiáveis nas configurações do aparelho).

## Como executar localmente

```bash
git clone https://github.com/Glawther/NutriScan.git
cd NutriScan

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

Acesse `http://127.0.0.1:8096` no navegador. A documentação da API OpenAPI fica em `http://127.0.0.1:8096/docs`.

## Testes

```bash
pytest tests/ -v
node --test tests/js/label_parser.test.js
```

## Licença

MIT.
