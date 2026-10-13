# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adota o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.8.0] - 2026-10-13

### Adicionado
- Implementação nativa da View Transitions API (`document.startViewTransition`) com degradação suave para navegadores e WebViews sem suporte.
- Transições fluidas de navegação lateral entre abas (`tab-panel`) com duração calibrada entre 150ms e 210ms e curva `cubic-bezier(0.2, 0, 0, 1)`.
- Animações refinadas de abertura e fechamento para modais (`#modal-profile-onboarding`, `#modal-whats-new`, `#modal-app-tour`).
- Atualizações contínuas de layout ao inserir ou remover itens no diário alimentar (`#meal-list`) e métricas do anel diário (`#diet-kpi-strip`).
- Conformidade total com preferências de acessibilidade `@media (prefers-reduced-motion: reduce)`, desativando animações quando solicitado pelo sistema.
- Suíte automatizada de testes cobrindo ativação de View Transitions e comportamento de fallback.

## [1.7.0] - 2026-10-13

### Adicionado
- Novo tema Minimalista Branco com Verde Esmeralda (Clean & Minimal), projetado para máxima legibilidade e clareza.
- Exportador de relatório diário em PDF estilizado para impressão e compartilhamento com nutricionistas.
- Modal interativo "O que há de novo" acessível diretamente pelo topo da interface.
- Novas capturas de tela em alta resolução no README.md cobrindo todos os módulos no novo padrão visual.

### Modificado
- Reformulação completa da hierarquia visual com base nas diretrizes do Web Interface Guidelines e WCAG AA.
- Otimização do layout flexível para dispositivos móveis, eliminando quebras em telas estreitas (412px).
- Sincronização automatizada dos recursos estáticos com a distribuição do aplicativo Android (.APK).

## [1.4.0] - 2026-10-13

### Adicionado
- Modal interativo "O que há de novo" com resumo das melhorias e acesso direto pelo topo da página.
- Indicador discreto de versão no topo da interface.

### Modificado
- Redesign minimalista completo com foco em fundo branco, cartões limpos e destaques em verde esmeralda.
- Eliminação de elementos visuais excessivos, sombras pesadas e ruídos gráficos para proporcionar leitura clara.
- Ajuste rigoroso de contraste de cores atendendo ao padrão WCAG AA em textos, botões e indicadores.
- Simplificação da linguagem de toda a interface, com textos diretos e sem termos técnicos desnecessários.
- Layout flexível aprimorado para telas pequenas, eliminando rolagem horizontal indesejada no celular.

## [1.3.0] - 2026-10-13

### Adicionado
- Criação de perfil do usuário com cálculo metabólico baseado na equação científica Mifflin-St Jeor.
- Sugestão automática de metas de calorias, proteínas, carboidratos, gorduras e ingestão de água com base no objetivo pessoal (emagrecimento, manutenção ou ganho muscular).
- Piso de segurança nutricional que impede metas inferiores a 1200 kcal para mulheres e 1500 kcal para homens.
- Tour guiado passo a passo com cinco etapas destacando os principais recursos do aplicativo.
- Inicialização com estado zerado no primeiro uso, permitindo que o usuário comece seu diário alimentar sem registros fictícios pré-carregados.

### Corrigido
- Proteção de segurança contra injeção de código em campos de texto.
- Ajuste no fuso horário local para garantir que os registros do diário reflitam com precisão o dia corrente.
- Auditoria concorrente de qualidade e experiência validando o fluxo para usuários básicos, avançados e profissionais de saúde.

## [1.2.0] - 2026-10-13

### Adicionado
- Scanner de foto do prato com reconhecimento visual que funciona totalmente sem internet.
- Catálogo nutricional de mais de 150 alimentos baseado na Tabela Brasileira de Composição de Alimentos (TACO).
- Estimativa visual de porções e gramaturas com ajuste manual rápido de porção.
- Balanço de seis micronutrientes essenciais (cálcio, ferro, sódio, potássio, vitamina C e fibras) com percentual da ingestão diária recomendada pela ANVISA.
- Registro rápido do prato completo diretamente no diário de alimentação.

## [1.1.0] - 2026-10-13

### Adicionado
- Leitor de foto de ficha técnica nutricional com extração óptica e cálculo proporcional.
- Classificação e alertas de rotulagem frontal segundo as normas da ANVISA (RDC 429/2020 e IN 75/2020) para excesso de açúcares adicionados, gorduras saturadas e sódio.
- Scanner de código de barras em tempo real utilizando a câmera do dispositivo com foco e suporte a lanterna.
- Comparador lado a lado de alimentos para auxiliar na escolha da opção mais saudável no ponto de venda.
- Registro diário de consumo de água com barra de progresso.
- Exportação de relatório diário formatado diretamente para compartilhamento no WhatsApp.

## [1.0.0] - 2026-10-12

### Adicionado
- Lançamento inicial do NutriScan com painel web e aplicativo Android WebView.
- Diário alimentar para registro de refeições (café da manhã, almoço, lanche e jantar).
- Cálculo em tempo real de calorias e macronutrientes consumidos ao longo do dia.
- Catálogo de produtos integrado com suporte a funcionamento offline.
- Consulta de informações nutricionais completas e ingredientes de produtos embalados.
- Integração com base de dados aberta para busca rápida de alimentos por código de barras.