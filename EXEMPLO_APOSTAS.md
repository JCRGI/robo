# Exemplo de uso do Robô com Swipe para Apostas

Este arquivo demonstra como usar as novas funcionalidades do robô para fazer swipe na tela, atualizar e verificar textos de apostas.

## Funcionalidades Implementadas

### 1. Swipe Duplo para Atualização Completa

- O robô agora pode fazer swipe duplo para garantir atualização completa da tela
- Especialmente útil para apps que precisam de refresh mais intensivo

### 2. Busca Específica por Apostas

- Modo especial que busca automaticamente por palavras relacionadas a apostas
- Lista padrão: ["aposta", "bet", "apostar", "odds", "stake", "wager"]
- Possibilidade de personalizar as palavras buscadas

### 3. Interface Melhorada

- Checkboxes para ativar swipe duplo
- Checkbox para modo de busca de apostas
- Campo para definir palavras customizadas
- Botões específicos para diferentes tipos de automação

## Como Usar

### Via Interface Web

1. **Bot Normal com Swipe Duplo:**

   - Marque a opção "Swipe Duplo"
   - Digite o texto alvo desejado
   - Clique em "Iniciar Normal"

2. **Bot Específico para Apostas:**

   - Opcionalmente, defina palavras personalizadas no campo "Palavras de Apostas"
   - Clique em "🎯 Iniciar Bot Apostas"
   - O bot automaticamente procurará por termos relacionados a apostas

3. **Bot com Refresh Otimizado:**
   - Digite o texto alvo
   - Clique em "🔄 Iniciar com Refresh"
   - Usará swipe duplo automaticamente

### Via API REST

#### Iniciar Bot de Apostas:

```bash
curl -X POST http://localhost:5000/bots/apostas/start \
  -H "Content-Type: application/json" \
  -d '{
    "porta": 5560,
    "intervalo": 3,
    "notify_whatsapp": false,
    "swipe_duplo": true,
    "palavras_apostas": ["aposta", "bet", "odds"]
  }'
```

#### Iniciar Bot com Refresh Otimizado:

```bash
curl -X POST http://localhost:5000/bots/refresh/start \
  -H "Content-Type: application/json" \
  -d '{
    "porta": 5560,
    "texto_alvo": "comprar",
    "novo_texto": "100.00",
    "intervalo": 2,
    "swipe_duplo": true
  }'
```

#### Iniciar Bot Normal com Configurações Avançadas:

```bash
curl -X POST http://localhost:5000/bots/start \
  -H "Content-Type: application/json" \
  -d '{
    "porta": 5560,
    "texto_alvo": "aposta",
    "intervalo": 3,
    "swipe_duplo": true,
    "buscar_apostas": true,
    "notify_whatsapp": true,
    "palavras_apostas": ["bet", "stake", "wager"]
  }'
```

## Parâmetros Disponíveis

### BotConfig

- `serial`: Serial do emulador
- `texto_alvo`: Texto específico a procurar
- `novo_texto`: Texto para substituir (opcional)
- `intervalo`: Intervalo entre ciclos em segundos
- `usar_swipe`: Habilita swipe para refresh (padrão: true)
- `swipe_duplo`: Faz swipe duplo para melhor atualização
- `buscar_apostas`: Ativa modo de busca específica para apostas
- `palavras_apostas`: Lista personalizada de palavras para buscar
- `espera_pos_swipe`: Tempo de espera após swipe
- `notify_whatsapp`: Enviar notificação WhatsApp quando encontrar

## Fluxo de Funcionamento

### Ciclo Normal:

1. Faz swipe na tela (de 70% para 30% da altura)
2. Se `swipe_duplo` ativo, faz segundo swipe após 0.5s
3. Aguarda `espera_pos_swipe` segundos
4. Busca pelo texto usando UIAutomator
5. Se encontrado, clica e opcionalmente substitui texto
6. Aguarda `intervalo` segundos e repete

### Ciclo de Apostas:

1. Faz swipe(s) para atualizar tela
2. Percorre lista de palavras de apostas
3. Para cada palavra, tenta encontrar na tela
4. Se encontrar alguma, para o processo e notifica
5. Aguarda intervalo e repete

## Customizações Possíveis

### Palavras de Apostas Personalizadas

```python
# No código Python
palavras_personalizadas = ["jackpot", "premio", "ganhar", "lucro"]
```

### Ajuste de Coordenadas de Swipe

O swipe é calculado automaticamente baseado no tamanho da tela:

- X: Centro da tela (50%)
- Y inicial: 70% da altura
- Y final: 30% da altura
- Duração: 400ms

## Monitoramento

- Use o endpoint `/bots/status` para ver o status de todos os bots
- O log na interface mostra em tempo real o que está acontecendo
- Notificações WhatsApp podem ser configuradas para avisar quando encontrar apostas

## Dicas de Uso

1. **Para apps lentos**: Use `swipe_duplo=true` e aumente o `espera_pos_swipe`
2. **Para apostas específicas**: Use o bot de apostas com palavras personalizadas
3. **Para monitoramento**: Ative notificações WhatsApp
4. **Para teste**: Use intervalos menores (1-2s) e monitore o log
