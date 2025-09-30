# 🤖 Como Usar o Robô para Procurar Horários

## 📋 Funcionalidade

O robô foi simplificado para fazer exatamente o que você precisa:

1. **🔄 Faz "pull to refresh"** - puxa a tela de cima para baixo para atualizar o conteúdo (como no WhatsApp)
2. **🔍 Procura pelo texto/horário que você especificou**
3. **⏹️ Para automaticamente quando encontra o texto**
4. **📱 Pode notificar via WhatsApp quando encontrar** (opcional)

## 🚀 Como Usar

### 1. Iniciar o Sistema

```bash
python run.py
```

### 2. Acessar a Interface

- Abra http://127.0.0.1:5000 no navegador
- Você verá a lista de AVDs (emuladores) disponíveis

### 3. Configurar o Robô

Na seção **"Robô para Procurar Horário"**:

- **Porta**: Porta do emulador (ex: 5560, 5562)
- **Texto do horário**: O horário que você quer encontrar (ex: "15:30", "14:45")
- **Intervalo**: Tempo em segundos entre cada tentativa (padrão: 3s)
- **📱**: Marque se quer receber notificação no WhatsApp quando encontrar

### 4. Iniciar a Busca

- Clique no botão **"🔍 Iniciar Busca"**
- O robô vai começar a:
  1. Fazer swipe de cima para baixo
  2. Procurar pelo texto
  3. Repetir até encontrar
  4. Parar quando encontrar

### 5. Controlar o Robô

- **⏸️ Pausar/Retomar**: Pausa temporariamente
- **⏹️ Parar**: Para completamente
- **📊 Status**: Mostra informações detalhadas

## 📱 Notificação WhatsApp

Para receber notificações no WhatsApp, configure as variáveis de ambiente:

```bash
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_ID=seu_phone_id_aqui
WHATSAPP_TO=numero_destino_aqui
```

## 📊 Log de Atividades

O log mostra:

- ✅ Quando o robô inicia
- 🔍 O que está procurando
- 🔄 Cada tentativa (ciclo)
- ✅ Quando encontra o texto
- ⏹️ Quando para

## 💡 Exemplo de Uso

1. Emulador na porta 5560
2. Procurando horário "15:30"
3. Verificando a cada 3 segundos
4. Com notificação WhatsApp ativada

O robô vai:

- Fazer "pull to refresh" (puxar de cima para baixo) para atualizar o conteúdo
- Procurar "15:30" na tela
- Se não encontrar, aguardar 3s e repetir o pull to refresh
- Se encontrar, parar e notificar no WhatsApp

## ⚠️ Importante

- O emulador deve estar rodando e conectado
- O app deve estar aberto na tela onde aparece o horário
- O texto deve estar visível na tela após o swipe
- O robô para automaticamente quando encontra o texto

## 🔧 Solução de Problemas

### Robô não encontra o texto

- Verifique se o texto está escrito exatamente como aparece na tela
- Teste manualmente fazendo "pull to refresh" (puxar de cima para baixo) para ver se o texto aparece
- O texto deve estar visível após o pull to refresh
- Certifique-se que o app suporta pull to refresh

### Emulador não aparece

- Verifique se o emulador está rodando
- Execute `adb devices` no terminal para confirmar
- Reinicie o emulador se necessário

### Erro de conexão

- Verifique se o ADB está funcionando
- Reinicie o servidor ADB: `adb kill-server` e `adb start-server`
