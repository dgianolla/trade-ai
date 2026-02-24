# MVP Inicial do Usuário para Módulo Plantas (Referência)

1. **Upload Inicial**:
   a. Usuário envia URL da imagem da planta de uma loja.
   b. Usuário envia "Configuração Padrão de Loja" (ex: Loja Tipo A precisa de 30% display Coca, 20% Pepsi).
   
2. **Processamento da Imagem (OCR e Visão)**:
   a. Extrair texto (EasyOCR) para identificar marcas nas caixas/frentes.
   b. Detectar produtos/marcas.
   
3. **Análise de Regras de Negócio**:
   a. Cruzar o que foi detectado com a Configuração Padrão.
   b. Identificar:
      - Share de gôndola atual vs ideal.
      - Rupturas visíveis (espaços vazios marcados para aquela marca).
      
4. **Armazenamento e Retorno**:
   a. Salvar imagem no MinIO.
   b. Gravar metadata estruturado.
   c. Retornar JSON com o diagnóstico (conformidades e inconformidades).
