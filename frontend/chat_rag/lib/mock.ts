// Respostas simuladas da API, para testar o frontend sem chamar o Gemini/Cloud Run (que tem custo).
// Ative com NEXT_PUBLIC_API_MOCK=1 no .env.development.local.

import type { ExecResult } from './api'

const PROGRAMA_NEGOCIACAO = `from maspy import *

class Seller(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("sell"))

    @pl(gain, Goal("sell"))
    def offer(self, src):
        self.print("Oferecendo 42 ao Buyer")
        self.send("Buyer", tell, Belief("price", 42))
        self.stop_cycle()

class Buyer(Agent):
    @pl(gain, Belief("price", Any))
    def evaluate(self, src, price):
        if price < 50:
            self.print(f"Aceito o preço {price}")
            self.stop_cycle()
        else:
            self.send(src, achieve, Goal("sell"))

if __name__ == "__main__":
    seller, buyer = Seller("Seller"), Buyer("Buyer")
    Admin().start_system()`

const PROGRAMA_COM_MERCADO = `from maspy import *

class Market(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        self.create(Percept("stock", 10))

    def sell_item(self, src):
        stock = self.get(Percept("stock", Any))
        self.change(stock, stock.values - 1)

class Seller(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("sell"))

    @pl(gain, Goal("sell"))
    def offer(self, src):
        self.print("Oferecendo 42 ao Buyer")
        self.send("Buyer", tell, Belief("price", 42))
        self.stop_cycle()

class Buyer(Agent):
    @pl(gain, Belief("price", Any))
    def evaluate(self, src, price):
        if price < 50:
            self.sell_item()
            self.print(f"Aceito o preço {price}")
            self.stop_cycle()
        else:
            self.send(src, achieve, Goal("sell"))

if __name__ == "__main__":
    market = Market("Market")
    seller, buyer = Seller("Seller"), Buyer("Buyer")
    Admin().connect_to([seller, buyer], market)
    Admin().start_system()`

const RESPOSTA_DUVIDA = `Para enviar uma mensagem para outro agente use \`self.send(destinatario, ilocucao, conteudo)\` dentro de um plano.

1. Pedir que o outro agente realize um objetivo (\`achieve\`):
\`\`\`python
self.send("Recv", achieve, Goal("receive_info", msg))
\`\`\`

2. Informar uma crença (\`tell\`):
\`\`\`python
self.send(src, tell, Belief("info_received"))
\`\`\`

Exemplos usados: **ex-send-recv.py** e **ex-sample-messages.py**.`

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

export async function perguntarMock(pergunta: string): Promise<string> {
  await sleep(1200)
  const q = pergunta.toLowerCase()

  if (q.includes('erro')) {
    throw new Error('Cota da API Gemini esgotada. Tente novamente mais tarde. (simulado)')
  }
  // Pedido de alteração: o frontend envia o código atual junto com a pergunta
  if (q.includes('código maspy atual')) {
    return `Adicionei um ambiente **Market** com um \`Percept\` de estoque, e conectei os dois agentes a ele. O comprador consome uma unidade ao aceitar o preço.\n\n\`\`\`python\n${PROGRAMA_COM_MERCADO}\n\`\`\``
  }
  if (/vendedor|comprador|negoci|seller|buyer/.test(q)) {
    return `Pronto. O **Seller** oferece um preço e o **Buyer** aceita valores abaixo de 50 ou pede uma nova oferta.\n\n\`\`\`python\n${PROGRAMA_NEGOCIACAO}\n\`\`\``
  }
  return RESPOSTA_DUVIDA
}

/** Saída no formato real do runner (capturada de uma execução do maspy-ml 2026.5.13). */
export async function executarMock(codigo: string): Promise<ExecResult> {
  await sleep(900)
  if (/raise |erro_simulado/.test(codigo)) {
    return {
      status: 'erro',
      saida: '',
      erro: 'Traceback (most recent call last):\n  File "maspy_system.py", line 3, in <module>\nValueError: falhou aqui',
      duracao_s: 0.7,
    }
  }
  const agentes = [...codigo.matchAll(/^class\s+(\w+)\s*\(\s*Agent\s*\)/gm)].map(m => m[1])
  return {
    status: 'tempo_esgotado',
    saida: [
      '# Admin #> Starting MASPY Program - ver.2026.05.13',
      '# Admin #> Starting All Agents',
      '# Admin #> Starting System',
      ...agentes.map(a => `Agent:${a}> Olá, eu sou ${a} (simulado)`),
    ].join('\n'),
    erro: '',
    duracao_s: 10.01,
  }
}
