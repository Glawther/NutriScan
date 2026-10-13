# Changelog

Todas as mudancas notaveis neste projeto serao documentadas neste arquivo.

O formato e baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adota o [Versionamento Semantico](https://semver.org/lang/pt-BR/).

## [1.4.0] - 2026-10-13

### Adicionado
- Modal interativo "O que ha de novo" com resumo das melhorias e acesso direto pelo topo da pagina.
- Indicador discreto de versao no topo da interface.

### Modificado
- Redesign minimalista completo com foco em fundo branco, cartoes limpos e destaques em verde esmeralda.
- Eliminacao de elementos visuais excessivos, sombras pesadas e ruidos graficos para proporcionar leitura clara.
- Ajuste rigoroso de contraste de cores atendendo ao padrao WCAG AA em textos, botoes e indicadores.
- Simplificacao da linguagem de toda a interface, com textos diretos e sem termos tecnicos desnecessarios.
- Layout flexivel aprimorado para telas pequenas, eliminando rolagem horizontal indesejada no celular.

## [1.3.0] - 2026-10-13

### Adicionado
- Criacao de perfil do usuario com calculo metabolico baseado na equacao cientifica Mifflin-St Jeor.
- Sugestao automatica de metas de calorias, proteinas, carboidratos, gorduras e ingestao de agua com base no objetivo pessoal (emagrecimento, manutencao ou ganho muscular).
- Piso de seguranca nutricional que impede metas inferiores a 1200 kcal para mulheres e 1500 kcal para homens.
- Tour guiado passo a passo com cinco etapas destacando os principais recursos do aplicativo.
- Inicializacao com estado zerado no primeiro uso, permitindo que o usuario comece seu diario alimentar sem registros ficticios pre-carregados.

### Corrigido
- Protecao de seguranca contra injecao de codigo em campos de texto.
- Ajuste no fuso horario local para garantir que os registros do diario reflitam com precisao o dia corrente.
- Auditoria concorrente de qualidade e experiencia validando o fluxo para usuarios basicos, avancados e profissionais de saude.

## [1.2.0] - 2026-10-13

### Adicionado
- Scanner de foto do prato com reconhecimento visual que funciona totalmente sem internet.
- Catalogo nutricional de mais de 150 alimentos baseado na Tabela Brasileira de Composicao de Alimentos (TACO).
- Estimativa visual de porcoes e gramaturas com ajuste manual rapido de porcao.
- Balanco de seis micronutrientes essenciais (calcio, ferro, sodio, potassio, vitamina C e fibras) com percentual da ingestao diaria recomendada pela ANVISA.
- Lancamento rapido do prato completo diretamente no diario de alimentacao.

## [1.1.0] - 2026-10-13

### Adicionado
- Leitor de foto de ficha tecnica nutricional com reconhecimento de texto inteligente.
- Classificacao e alertas de rotulagem frontal segundo as normas da ANVISA (RDC 429/2020 e IN 75/2020) para excesso de acucares adicionados, gorduras saturadas e sodio.
- Scanner de codigo de barras em tempo real utilizando a camera do dispositivo com foco e suporte a lanterna.
- Comparador lado a lado de alimentos para auxiliar na escolha da opcao mais saudavel no ponto de venda.
- Registro diario de consumo de agua com barra de progresso.
- Exportacao de relatorio diario formatado diretamente para compartilhamento no WhatsApp.

## [1.0.0] - 2026-10-12

### Adicionado
- Lancamento inicial do NutriScan com painel web e aplicativo Android WebView.
- Diario alimentar para registro de refeicoes (cafe da manha, almoco, lanche e jantar).
- Calculo em tempo real de calorias e macronutrientes consumidos ao longo do dia.
- Catalogo de produtos integrado com suporte a funcionamento offline.
- Consulta de informacoes nutricionais completas e ingredientes de produtos embalados.
- Integracao com base de dados aberta para busca rapida de alimentos por codigo de barras.