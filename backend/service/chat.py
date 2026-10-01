import sys
import os
import re
import time
import json
import signal
import threading
from datetime import datetime

# Configuração de encoding para garantir compatibilidade com caracteres especiais no Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Adiciona o caminho base para permitir importações do projeto local
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sandbox de validação em malha fechada (self-debugging)
from sandbox import run_in_sandbox, parse_traceback, DebugMemory, CONFIG

# Importações resilientes do ecossistema LangChain e ChromaDB
try:
    from langchain_chroma import Chroma
except Exception:
    from langchain_community.vectorstores import Chroma

try:
    from langchain_ollama import OllamaLLM as ChatOllama, OllamaEmbeddings
except Exception:
    from langchain_community.llms import Ollama as ChatOllama
    from langchain_community.embeddings import OllamaEmbeddings

# Importações do projeto local
from service.config import EMBEDDING_DIR, LLM_MODEL, EMBEDDING_MODEL, OLLAMA_BASE_URL

# Tenta importar um modelo específico para o Revisor (se configurado no config.py), senão usa o padrão
try:
    from service.config import REVISOR_MODEL
except ImportError:
    REVISOR_MODEL = LLM_MODEL  # Fallback: se não houver um LLM mais forte configurado, usa o mesmo

from service.retriever import MaspyEntityRetriever

# ==============================================================================
# 1. MOTOR DE PÓS-PROCESSAMENTO (V5.1 - PREVENÇÃO DE AMNÉSIA DE CONTEXTO)
# ==============================================================================

class MaspySanitizer:
    """
    Pipeline de Sanitização Orientado a Objetos.
    Cada método ataca uma alucinação específica do LLM, garantindo código MASPY perfeito.
    """
    def __init__(self, code: str):
        self.code = code
        self.fixes = []

    def execute_pipeline(self) -> str:
        """Executa a cadeia de responsabilidade para limpar o código."""
        if not self.code: return ""
        
        self._clean_imports()
        self._deduplicate_main()
        self._fix_plan_signatures()
        self._sync_instance_names()
        self._fix_send_targets()
        self._fix_rogue_channels()
        self._fix_sends_to_env()
        self._map_strict_methods()
        self._fix_environment_actions()
        self._ensure_stop_cycle_after_action()
        self._fix_empty_beliefs_percepts()
        self._fix_extreme_hallucinations()
        self._fix_direct_assignments()
        self._ensure_inits_and_context() # NOVA PROTEÇÃO V5.1
        self._clean_orphans()
        self._ensure_clean_startup()
        self._fix_admin_connect()
        self._add_header()
        
        if self.fixes:
            print(f"[POST-PROCESS] 🔧 {', '.join(set(self.fixes))}")
            
        return self.code.strip()

    def _clean_imports(self):
        self.code = re.sub(r'^\s*(?:from\s+maspy\s+import\s+.*|import\s+maspy)\s*$', '', self.code, flags=re.MULTILINE)

    def _deduplicate_main(self):
        main_matches = list(re.finditer(r'if __name__ == "__main__":', self.code))
        if len(main_matches) > 1:
            parts = re.split(r'if __name__ == "__main__":', self.code)
            classes_part = parts[0]
            main_part = parts[-1]
            self.code = classes_part + '\n\nif __name__ == "__main__":' + main_part
            self.fixes.append("Consolidação de blocos __main__")

    def _fix_plan_signatures(self):
        def inject_args(m):
            header, indent, func, args = m.groups()
            args_clean = args.strip()
            if 'src' not in args_clean:
                if 'self' in args_clean: args_clean = args_clean.replace('self', 'self, src')
                else: args_clean = f"self, src, {args_clean}" if args_clean else "self, src"
            if '*args' not in args_clean:
                args_clean += ', *args'
            return f"{header}{indent}def {func}({args_clean.strip(', ')}):"
        self.code = re.sub(r'(@pl\(.*?\)\s*\n)(\s*)def\s+(\w+)\s*\((.*?)\):', inject_args, self.code, flags=re.DOTALL)

    def _sync_instance_names(self):
        def sync(m):
            var_name, class_name, str_name = m.groups()
            if class_name != str_name:
                self.fixes.append(f"Nome da instância sincronizado: '{str_name}' -> '{class_name}'")
            return f'{var_name} = {class_name}("{class_name}")'
        self.code = re.sub(r'^(\s*[a-zA-Z0-9_]+)\s*=\s*([A-Z]\w*)\([\'"]([^\'"]+)[\'"]\)', sync, self.code, flags=re.MULTILINE)

    def _fix_send_targets(self):
        def fix_suffix(m):
            prefix, target, suffix = m.group(1), m.group(2), m.group(3)
            if target != 'src' and not target.endswith('_1') and target != 'default':
                return f'{prefix}"{target}_1"{suffix}'
            return m.group(0)
        self.code = re.sub(r'(self\.send\()[\'"]([a-zA-Z0-9_]+)[\'"](,)', fix_suffix, self.code)

    def _fix_rogue_channels(self):
        def remove_channels(m):
            base_send, canal = m.group(1), m.group(2)
            if "Channel" not in canal and canal != "default":
                self.fixes.append(f"Removido argumento inválido do send: '{canal}'")
                return base_send + ")"
            return m.group(0)
        self.code = re.sub(r'(self\.send\([^,]+,\s*[^,]+,\s*(?:Goal|Belief)\([^)]+\))\s*,\s*["\']([^"\']+)["\']\)', remove_channels, self.code)

    def _fix_sends_to_env(self):
        env_names = re.findall(r'class\s+([a-zA-Z0-9_]+)\s*\(Environment\):', self.code)
        for env_name in env_names:
            def replace_send(m):
                indent = m.group(1)
                self.fixes.append(f"Impedido envio BDI para o ambiente '{env_name}'. Transformado em espera ativa.")
                return f'{indent}self.wait(1)\n{indent}self.send(self.my_name, {m.group(2)}, {m.group(3)})'
            self.code = re.sub(rf'^([ \t]*)self\.send\(\s*["\']{env_name}(?:_1)?["\']\s*,\s*([^,]+)\s*,\s*((?:Goal|Belief)\([^)]+\))\s*\)', replace_send, self.code, flags=re.MULTILINE)

    def _map_strict_methods(self):
        if '.remove(' in self.code: self.code = self.code.replace('.remove(', '.rm(')
        self.code = re.sub(r'\.add_goal\(', '.add(', self.code)
        self.code = re.sub(r'\.add_belief\(', '.add(', self.code)
        
        def fix_change(m):
            self.fixes.append("Mapeado self.change() para self.rm() e self.add() (APENAS Beliefs)")
            return f'self.rm({m.group(1)})\n        self.add({m.group(1).replace(m.group(1).split(",")[-1].strip(" )"), m.group(2))})'
        self.code = re.sub(r'self\.change\(\s*(Belief)\(([^)]+)\)\s*,\s*([^)]+)\)', fix_change, self.code)

    def _fix_environment_actions(self):
        env_methods = {}
        env_blocks = re.finditer(r'class\s+([a-zA-Z0-9_]+)\s*\(Environment\):(.*?)(?=(?:\nclass\s+[a-zA-Z0-9_]+|if __name__ ==|\Z))', self.code, re.DOTALL)
        for env_match in env_blocks:
            env_name = env_match.group(1)
            methods = re.findall(r'def\s+([a-zA-Z0-9_]+)\s*\(', env_match.group(2))
            env_methods[env_name] = [m for m in methods if m != '__init__']

        if not env_methods:
            return

        for env_name, methods in env_methods.items():
            for method in methods:
                def fix_direct(m):
                    self.fixes.append(f"Chamada direta corrigida: '{method}'")
                    return f'self.action("{env_name}").{method}(self.my_name)'
                self.code = re.sub(rf'self\.{method}\(\s*[^)]*\s*\)', fix_direct, self.code)

        for env_name, methods in env_methods.items():
            if not methods: continue
            default_method = methods[0] 
            
            def purify_action_chain(m):
                chain = m.group(1) 
                if not chain.strip():
                    self.fixes.append(f"Ação vazia injetada com método real: '{default_method}'")
                    return f'self.action("{env_name}").{default_method}(self.my_name)'

                found_method = None
                for method in methods:
                    if method in chain:
                        found_method = method
                        break
                
                if not found_method:
                    found_method = default_method
                    self.fixes.append(f"Alucinação severa ({chain.strip()}) substituída pela ação real '{found_method}'")
                else:
                    self.fixes.append(f"Cadeia alucinada redirecionada e limpa para '{found_method}'")
                return f'self.action("{env_name}").{found_method}(self.my_name)'
            
            self.code = re.sub(rf'self\.action\(\s*["\']{env_name}["\']\s*\)((?:[ \t]*\.[a-zA-Z0-9_]+[ \t]*\([^)]*\)[ \t]*)*)', purify_action_chain, self.code)
            
        def fix_orphan(m):
            indent = m.group(1)
            action_name = m.group(2).strip(chr(34)+chr(39))
            if not env_methods:
                self.fixes.append(f"Aviso: Ação '{action_name}' mantida órfã (nenhum ambiente detectado no código)")
                return m.group(0)
            env_name = list(env_methods.keys())[0]
            self.fixes.append(f"Injetado ambiente '{env_name}' na ação '{action_name}'")
            return f'{indent}self.action("{env_name}").{action_name}(self.my_name)'
            
        self.code = re.sub(r'^([ \t]*)self\.action\(\s*(["\'][a-zA-Z0-9_]+["\'])\s*\)(?!\s*\.)', fix_orphan, self.code, flags=re.MULTILINE)

    def _ensure_stop_cycle_after_action(self):
        lines = self.code.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if re.search(r'^[ \t]*self\.action\([^)]+\)\.[a-zA-Z0-9_]+\([^)]*\)', line):
                has_stop = False
                for j in range(1, 4):
                    if i + j < len(lines):
                        next_line = lines[i+j].strip()
                        if 'self.stop_cycle()' in next_line:
                            has_stop = True
                            break
                        if next_line.startswith('def ') or next_line.startswith('@pl'):
                            break
                if not has_stop:
                    indent = re.match(r'^([ \t]*)', line).group(1)
                    new_lines.append(f'{indent}self.stop_cycle()  # Injetado pelo Sanitizer')
                    self.fixes.append("Injetado stop_cycle() ausente após ação de ambiente")
        self.code = '\n'.join(new_lines)

    def _fix_empty_beliefs_percepts(self):
        def fix_three_args(m):
            self.fixes.append("Removido 3º argumento inválido do Belief/Percept")
            return f'{m.group(1)}({m.group(2)}, {m.group(3)})'
        self.code = re.sub(r'(Belief|Percept)\(\s*(["\'][a-zA-Z0-9_]+["\'])\s*,\s*([^,)]+)\s*,\s*[^)]+\)', fix_three_args, self.code)

        def fill_empty(m):
            self.fixes.append(f"Preenchido valor ausente no {m.group(2)}")
            return f'{m.group(1)}{m.group(2)}({m.group(3)}, True)'
        self.code = re.sub(r'(self\.(?:add|rm)\(\s*)(Belief|Percept)\(\s*(["\'][a-zA-Z0-9_]+["\'])\s*\)', fill_empty, self.code)

    def _fix_extreme_hallucinations(self):
        self.code = re.sub(r'self\.rm\(\s*Percept\s*\)', 'self.rm(Percept("indefinido", True))', self.code)
        self.code = re.sub(r'self\.add\(\s*Percept\s*\)', 'self.add(Percept("indefinido", True))', self.code)
        self.code = re.sub(r'self\.rm\(\s*Belief\s*\)', 'self.rm(Belief("indefinido", True))', self.code)
        self.code = re.sub(r'self\.add\(\s*Belief\s*\)', 'self.add(Belief("indefinido", True))', self.code)

    def _fix_direct_assignments(self):
        def fix_assign(m):
            self.fixes.append("Mapeada atribuição direta para método .add()")
            return f'{m.group(1)}.add({m.group(2)})'
        self.code = re.sub(r'([a-zA-Z0-9_]+)\.(?:goal|belief)\s*=\s*((?:Goal|Belief)\([^)]+\))', fix_assign, self.code)

    def _ensure_inits_and_context(self):
        """NOVA V5.1: Garante que os agentes possuam __init__ e crenças exigidas nos seus planos."""
        agent_blocks = re.finditer(r'class\s+([a-zA-Z0-9_]+)\s*\(Agent\):(.*?)(?=(?:\nclass\s+[a-zA-Z0-9_]+|if __name__ ==|\Z))', self.code, re.DOTALL)
        new_code = self.code
        
        for match in agent_blocks:
            cls_name = match.group(1)
            cls_body = match.group(2)
            
            # Extrai Beliefs requeridos pelos @pl do agente
            contexts = re.findall(r'@pl\(.*?Belief\(([^)]+)\).*?\)', cls_body)
            required_beliefs = []
            for ctx in contexts:
                parts = [p.strip() for p in ctx.split(',')]
                # Ignorar verificações soltas de Any, None ou False
                if len(parts) == 2 and parts[1] not in ['Any', 'None']:
                    required_beliefs.append(f'self.add(Belief({parts[0]}, {parts[1]}))')
            
            required_beliefs = list(set(required_beliefs))
            
            if 'def __init__' not in cls_body:
                # O LLM esqueceu-se do __init__, vamos injetá-lo!
                init_block = f"\n    def __init__(self, agt_name):\n        super().__init__(agt_name)"
                for b in required_beliefs:
                    init_block += f"\n        {b}"
                init_block += "\n"
                
                class_decl = f"class {cls_name}(Agent):"
                new_code = new_code.replace(class_decl, class_decl + init_block, 1)
                self.fixes.append(f"Injetado __init__ e crenças ausentes em '{cls_name}'")
            else:
                # Se o __init__ já existir, apenas injetamos as crenças que faltarem
                init_match = re.search(r'(def __init__.*?super\(\)\.__init__[^)\n]*\))', cls_body, re.DOTALL)
                if init_match:
                    injection = ""
                    for b in required_beliefs:
                        if b not in cls_body:
                            injection += f"\n        {b}"
                    if injection:
                        new_code = new_code.replace(init_match.group(1), init_match.group(1) + injection, 1)
                        self.fixes.append(f"Injetadas crenças no __init__ de '{cls_name}'")
                        
        self.code = new_code

    def _clean_orphans(self):
        lines = self.code.split('\n')
        new_lines = []
        in_main = False
        for line in lines:
            if 'if __name__ == "__main__":' in line: in_main = True
            if not in_main and re.match(r'^\s*[a-zA-Z0-9_]+\s*=\s*[A-Z]\w*\([\'"].*?[\'"]\)', line):
                continue
            new_lines.append(line)
        self.code = '\n'.join(new_lines)

    def _ensure_clean_startup(self):
        # Remove qualquer Admin().start_system() existente
        self.code = re.sub(r'\n?\s*Admin\(\)\.start_system\(\)', '', self.code)

        if 'if __name__ == "__main__":' not in self.code:
            return

        # Garante console_settings logo após o if __name__
        if 'console_settings' not in self.code:
            self.code = self.code.replace(
                'if __name__ == "__main__":',
                'if __name__ == "__main__":\n    Admin().console_settings(True)'
            )

        # Encontra a última linha que pertence ao bloco __main__
        # (indentada com 4 espaços e que seja código Python real)
        lines = self.code.split('\n')
        last_code_idx = -1
        in_main = False
        for i, line in enumerate(lines):
            if 'if __name__ == "__main__":' in line:
                in_main = True
            if in_main and line.startswith('    ') and line.strip():
                last_code_idx = i

        if last_code_idx != -1:
            lines.insert(last_code_idx + 1, '    Admin().start_system()')
            # Remove tudo que vier depois do start_system (observações do LLM)
            self.code = '\n'.join(lines[:last_code_idx + 2])
            self.fixes.append("Admin().start_system() inserido como última linha do __main__")
        else:
            self.code = self.code.strip() + '\n    Admin().start_system()'

    def _fix_admin_connect(self):
        agent_classes = set(re.findall(r'class\s+([a-zA-Z0-9_]+)\s*\(Agent\):', self.code))
        env_classes = set(re.findall(r'class\s+([a-zA-Z0-9_]+)\s*\(Environment\):', self.code))

        var_map = {}
        for match in re.finditer(r'^([ \t]*)([a-zA-Z0-9_]+)\s*=\s*([A-Z]\w*)\(', self.code, flags=re.MULTILINE):
            var_name = match.group(2)
            class_name = match.group(3)
            if class_name in agent_classes:
                var_map[var_name] = 'Agent'
            elif class_name in env_classes:
                var_map[var_name] = 'Environment'
            elif class_name == 'Channel':
                var_map[var_name] = 'Channel'

        def rebuild_connect(m):
            list1_raw = m.group(1).replace("'", "").replace('"', "")
            list2_raw = m.group(2).replace("'", "").replace('"', "")
            
            all_items = [item.strip() for item in (list1_raw + "," + list2_raw).split(',')]
            
            agents_list = []
            envs_list = ["Channel()"] 
            
            for item in all_items:
                if not item or item == "Channel()":
                    continue
                
                if item in var_map:
                    if var_map[item] == 'Agent':
                        agents_list.append(item)
                    elif var_map[item] == 'Environment' or var_map[item] == 'Channel':
                        envs_list.append(item)
                else:
                    if any(item.lower().startswith(c.lower()) for c in env_classes) or "env" in item:
                        envs_list.append(item)
                    else:
                        agents_list.append(item)

            agents_list = list(dict.fromkeys(agents_list))
            envs_list = list(dict.fromkeys(envs_list))
            
            self.fixes.append("Reordenamento Topológico: Agentes na 1ª lista, Ambientes/Canais na 2ª lista")
            return f"Admin().connect_to([{', '.join(agents_list)}], [{', '.join(envs_list)}])"

        self.code = re.sub(r'Admin\(\)\.connect_to\(\s*\[(.*?)\],\s*\[(.*?)\]\s*\)', rebuild_connect, self.code)

    def _add_header(self):
        header = "# ==========================================================\n"
        header += "# CÓDIGO MASPY GERADO (V5.1 - PREVENÇÃO DE AMNÉSIA DE CONTEXTO)\n"
        header += "# ==========================================================\n"
        header += "from maspy import *\n\n"
        self.code = header + self.code.strip()

# ==============================================================================
# 2. FUNÇÕES AUXILIARES DE EXTRAÇÃO E AGENTES
# ==============================================================================

def extract_code_block(text: str) -> str:
    if not text: return ""

    # Caso 1: bloco ```python ... ``` bem formado
    match = re.search(r'```python\s*(.*?)\s*```', text, re.DOTALL)
    if match: return match.group(1).strip()

    # Caso 2: bloco ``` ... ``` sem linguagem
    match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    if match: return match.group(1).strip()

    # Caso 3: sem delimitadores — encontra início do código
    lines = text.split('\n')
    start_idx = -1
    for i, line in enumerate(lines):
        if 'from maspy' in line or line.startswith('class ') or 'if __name__' in line:
            start_idx = i
            break

    if start_idx == -1:
        return text.strip()

    code = '\n'.join(lines[start_idx:]).strip()

    # Corta tudo que vier após Admin().start_system() (observações do LLM)
    if 'Admin().start_system()' in code:
        code = code[:code.rfind('Admin().start_system()') + len('Admin().start_system()')]

    return code.strip()

def extract_main_only(text: str) -> str:
    code = extract_code_block(text)
    if 'if __name__ == "__main__":' in code:
        return 'if __name__ == "__main__":' + code.split('if __name__ == "__main__":')[-1]
    return code

def prompt_agente_arquiteto(question: str, context: str) -> str:
    return f"""Atue como AGENTE ARQUITETO MASPY. Projete as classes BDI com liberdade criativa para o problema, MAS sob as seguintes restrições inquebráveis:

!!! REGRAS DE SOBREVIVÊNCIA BDI E IOT !!!

1. DIFERENÇA CRÍTICA ENTRE AGENTE E AMBIENTE:
   - Em AGENTES (`class X(Agent):`): Para alterar crenças, use OBRIGATORIAMENTE `self.rm(Belief(...))` e `self.add(Belief(...))`. Agentes NÃO possuem o método `change`.
   - Em AMBIENTES (`class Y(Environment):`): Para alterar percepções, use OBRIGATORIAMENTE `self.change(Percept("nome"), "novo_valor")`. Ambientes NÃO possuem os métodos `rm` ou `add`.

2. INTERAÇÃO DO AGENTE COM O AMBIENTE:
   - NUNCA use `self.send()` para se comunicar com um `Environment`.
   - A sintaxe CORRETA para agir no ambiente é APENAS UM ENCADEAMENTO com o nome do método REAL: `self.action("NomeDoAmbiente").metodo_valido(self.my_name)`
   - No Ambiente, defina funções comuns (sem `@pl`) que recebem `(self, src, *args)`.

3. CRENÇAS E PERCEPÇÕES (IMPORTANTE):
   - `Belief` e `Percept` recebem EXATAMENTE 2 ARGUMENTOS. Nunca 1, nunca 3.
   - CORRETO: `Belief("estado", Any)` ou `Belief("estado", "ligado")`

4. O PARADOXO DO RECEPTOR: O agente que recebe uma ordem NÃO PODE exigir um estado que ele ainda não tem no gatilho. 

5. CICLO DE VIDA (stop_cycle):
   - O agente DEVE chamar `self.stop_cycle()` ao concluir a sua tarefa final ou ao executar uma `self.action()` no ambiente. 
   - EXCEÇÃO: Se ele enviou um `self.send(..., achieve...)` a outro agente, ele NÃO PODE chamar `stop_cycle()`, senão morre antes de ouvir a resposta!

6. CONSTRUTORES (__init__):
   - Todos os Agentes e Ambientes DEVEM ter o método `__init__(self, agt_name)` chamando `super().__init__(agt_name)`.
   - SE um plano `@pl` exige um `Belief` (ex: `Belief("estado", "vermelho")`), você DEVE adicionar essa crença no `__init__` do Agente usando `self.add(Belief(...))`, senão o agente ficará Idle para sempre!

7. PROIBIDO gerar 'if __name__ == "__main__":'.

CONTEXTO RAG:
{context}

PEDIDO DO UTILIZADOR: {question}
CÓDIGO DAS CLASSES:"""

def prompt_agente_integrador(question: str, classes_code: str) -> str:
    return f"""Atue como AGENTE INTEGRADOR MASPY. Crie APENAS o bloco 'if __name__ == "__main__":'.

REGRAS OBRIGATÓRIAS DE INICIALIZAÇÃO:
1. Instancie TODOS os agentes e ambientes com nomes IDÊNTICOS às classes: ex: `carro_norte = CarroNorte("CarroNorte")`.
2. A FUNÇÃO `Admin().connect_to` RECEBE DUAS LISTAS DISTINTAS E EXATAS:
   - A PRIMEIRA LISTA é apenas para AGENTES: `[semaforo, carro_norte, carro_sul]`
   - A SEGUNDA LISTA é apenas para CANAIS E AMBIENTES: `[Channel(), ambiente1]`
   - Exemplo Perfeito: `Admin().connect_to([carro1, carro2], [Channel(), rua])`
3. Inicie atribuindo o Goal APENAS ao agente principal usando OBRIGATORIAMENTE `.add()` (ex: `ag1.add(Goal("..."))`). NUNCA use atribuições diretas como `ag1.goal = Goal(...)`.

CLASSES DISPONÍVEIS PARA INSTANCIAR:
{classes_code}

PEDIDO ORIGINAL: {question}
BLOCO MAIN:"""

def prompt_agente_revisor(question: str, generated_code: str) -> str:
    return f"""Atue como AGENTE REVISOR SÊNIOR MASPY. A sua tarefa é auditar e corrigir o código gerado pelos seus colegas.
Você é o último filtro de qualidade antes do código ser executado. Devolva APENAS o código Python corrigido e completo.

REVISE E CORRIJA OS SEGUINTES ERROS CRÍTICOS SE EXISTIREM:
1. Construtores e Crenças (MUITO IMPORTANTE): Verifique se todos os Agentes possuem `__init__`. Se um plano (`@pl`) usar uma condição (ex: `Belief("estado", "verde")`), GARANTA que existe um `self.add(Belief("estado", "verde"))` dentro do `__init__` do Agente!
2. Ciclo de Vida: Se um agente tem `self.send(..., achieve, Goal(...))` seguido de `self.stop_cycle()`, REMOVA o `stop_cycle()`. MAS, se o plano termina com `self.action()`, GARANTA que existe um `self.stop_cycle()` logo a seguir.
3. Topologia de Conexão: Verifique o `Admin().connect_to([lista1], [lista2])`. A `lista1` deve ter TODOS os agentes. A `lista2` deve ter APENAS `Channel()` e Ambientes. Nunca misture.
4. API de Ambientes: Ambientes usam `self.change(Percept("nome"), "valor")`. NUNCA usam `rm` ou `add`.
5. API de Agentes: Agentes usam `self.rm(Belief(...))` e `self.add(Belief(...))`. NUNCA usam `change`.
6. Ações no Ambiente: Devem ser encadeadas simples (`self.action("Ambiente").metodo(self.my_name)`). NUNCA envie `self.send` para Ambientes!

PEDIDO ORIGINAL: {question}

CÓDIGO A SER REVISADO:
{generated_code}

CÓDIGO CORRIGIDO (COM TUDO INCLUÍDO):"""

def prompt_agente_corretor(question: str, code: str, error_info: dict) -> str:
    """
    Diferente do Revisor (que audita estaticamente), o Corretor recebe o
    ERRO REAL de uma execução no sandbox. Usado no loop interno de
    self-debugging, após o código já ter passado por Arquiteto, Integrador,
    Revisor e Sanitizer mas ainda assim falhar ao rodar de verdade.
    """
    maspy_hint_section = (
        f"\nPISTA MASPY: {error_info['maspy_hint']}\n" if error_info.get("maspy_hint") else ""
    )
    return f"""Atue como AGENTE CORRETOR MASPY. O código abaixo foi executado de verdade
em ambiente de sandbox e FALHOU. Sua tarefa é corrigir o código com base no erro real,
não em suposições. Devolva APENAS o código Python corrigido e completo.

CATEGORIA DO ERRO: {error_info['category']}
TIPO: {error_info['exception_type']}
MENSAGEM: {error_info['message']}
{maspy_hint_section}
TRACEBACK COMPLETO:
{error_info['raw_traceback']}

REGRAS OBRIGATÓRIAS (as mesmas do Agente Revisor):
1. Agentes usam `self.rm(Belief(...))` / `self.add(Belief(...))`. Ambientes usam `self.change(Percept(...), valor)`. Nunca misture.
2. Se houve `self.send(..., achieve, Goal(...))`, NÃO chame `stop_cycle()` logo depois. Se o plano termina com `self.action()`, GARANTA `stop_cycle()` a seguir.
3. Se o erro for TimeoutError: garanta que todo loop/espera tenha uma condição de parada explícita e alcançável — provavelmente falta um `stop_cycle()`, uma crença nunca satisfeita, ou uma resposta que nunca chega.
4. Nunca use `self.send()` para falar com um `Environment`.

PEDIDO ORIGINAL: {question}

CÓDIGO QUE FALHOU:
{code}

CÓDIGO CORRIGIDO (COM TUDO INCLUÍDO):"""

# ==============================================================================
# 3. LÓGICA DE EXECUÇÃO
# ==============================================================================

stop_spinner = False
def _spinner():
    chars = ['|', '/', '-', '\\']
    i = 0
    while not stop_spinner:
        print(f"\r{chars[i % len(chars)]}", end='', flush=True)
        time.sleep(0.1)
        i += 1

class PipelineTimeoutError(Exception):
    """Levantada quando uma consulta inteira excede GLOBAL_TIMEOUT_SECONDS."""

def _run_with_global_timeout(fn, timeout_seconds):
    """
    Protege contra o pipeline inteiro ficar parado (ex: soma de vários
    ciclos internos/externos travando por tempo demais).
    Usa SIGALRM: só funciona na thread principal, em Linux/macOS.
    """
    def _raise_timeout(signum, frame):
        raise PipelineTimeoutError(f"Consulta excedeu {timeout_seconds}s (possível não-terminação).")

    old_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.alarm(timeout_seconds)
    try:
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def gerar_codigo_completo(query: str, context: str, llm_gerador, llm_revisor, failure_context: str = "") -> str:
    """
    Ciclo completo Arquiteto -> Integrador -> Revisor -> Sanitizer.
    `failure_context` (vindo da DebugMemory) é injetado no contexto RAG do
    Arquiteto quando esta é uma regeneração após falhas anteriores no sandbox.
    """
    context_completo = context
    if failure_context:
        context_completo = (
            f"{context}\n\n⚠️ TENTATIVAS ANTERIORES QUE FALHARAM NO SANDBOX "
            f"(evite repetir os mesmos erros):\n\n{failure_context}"
        )

    print(f"[DEBUG] 🏗️  Arquiteto a definir as classes ({LLM_MODEL})...")
    res_classes = llm_gerador.invoke(prompt_agente_arquiteto(query, context_completo))
    classes_code = extract_code_block(res_classes.content if hasattr(res_classes, 'content') else str(res_classes))
    if 'if __name__' in classes_code:
        classes_code = classes_code.split('if __name__')[0].strip()

    print(f"\n[DEBUG] 🔌 Integrador a montar as conexões ({LLM_MODEL})...")
    res_main = llm_gerador.invoke(prompt_agente_integrador(query, classes_code))
    main_code = extract_main_only(res_main.content if hasattr(res_main, 'content') else str(res_main))

    raw_combined_code = f"{classes_code}\n\n{main_code}"

    print(f"\n[DEBUG] 🧐 Revisor Sênior a auditar o código ({REVISOR_MODEL})...")
    res_revisor = llm_revisor.invoke(prompt_agente_revisor(query, raw_combined_code))
    reviewed_code = extract_code_block(res_revisor.content if hasattr(res_revisor, 'content') else str(res_revisor))

    sanitizer = MaspySanitizer(reviewed_code)
    return sanitizer.execute_pipeline()


def self_debugging_loop(code: str, query: str, llm_revisor, max_attempts: int = CONFIG.INNER_MAX_ATTEMPTS) -> dict:
    """
    LOOP INTERNO: executa o código no sandbox de verdade. Se falhar, manda
    o erro real (não suposição) para o Agente Corretor e tenta de novo.
    Correção local e barata — não regenera do zero.
    """
    history = []

    for attempt in range(1, max_attempts + 1):
        print(f"\n[SANDBOX] 🧪 Executando no sandbox (tentativa {attempt}/{max_attempts})...")
        result = run_in_sandbox(code)
        history.append({"attempt": attempt, "code": code, "result": result})

        if result["success"]:
            print(f"[SANDBOX] ✅ Execução validada.")
            return {"status": "validated", "code": code, "attempts": attempt, "history": history}

        error_info = parse_traceback(result["stderr"], status=result["status"])
        print(f"[SANDBOX] ❌ Falhou ({error_info['category']}): {error_info['exception_type']}: {error_info['message']}")

        if attempt < max_attempts:
            print(f"[DEBUG] 🩹 Corretor a consertar com base no erro real ({REVISOR_MODEL})...")
            res_corretor = llm_revisor.invoke(prompt_agente_corretor(query, code, error_info))
            corrected = extract_code_block(res_corretor.content if hasattr(res_corretor, 'content') else str(res_corretor))
            # Reaplica o sanitizer determinístico em cima da correção do LLM
            code = MaspySanitizer(corrected).execute_pipeline()

    return {"status": "failed_after_max_attempts", "code": code, "history": history}


def _log_run(query: str, result: dict) -> None:
    """Salva cada rodada em JSON — útil para métricas e gráficos de convergência no paper."""
    os.makedirs(CONFIG.LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(CONFIG.LOG_DIR, f"run_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"query": query, "result": result}, f, ensure_ascii=False, indent=2, default=str)


def processar_query_com_self_debugging(query: str, context: str, llm_gerador, llm_revisor) -> dict:
    """
    LOOP EXTERNO: encapsula geração + loop interno. Se o loop interno esgota
    as tentativas, guarda a falha em DebugMemory e reinicia do Arquiteto —
    útil quando o problema é estrutural (design do plano BDI), não sintático.
    Protegido por timeout global (não trava a consulta para sempre).
    """
    memory = DebugMemory()

    def _core():
        for outer_cycle in range(1, CONFIG.OUTER_MAX_CYCLES + 1):
            failure_context = memory.to_context()
            if outer_cycle > 1:
                print(f"\n[DEBUG] 🔁 Ciclo externo {outer_cycle}/{CONFIG.OUTER_MAX_CYCLES} — regenerando do Arquiteto com memória de falhas...")

            code = gerar_codigo_completo(query, context, llm_gerador, llm_revisor, failure_context)
            inner_result = self_debugging_loop(code, query, llm_revisor)

            if inner_result["status"] == "validated":
                return {
                    "status": "validated",
                    "code": inner_result["code"],
                    "outer_cycles": outer_cycle,
                    "inner_attempts": inner_result["attempts"],
                }

            error_history = [
                parse_traceback(h["result"]["stderr"], status=h["result"]["status"])
                for h in inner_result["history"]
                if not h["result"]["success"]
            ]
            memory.add_cycle(code=inner_result["code"], errors=error_history)

        return {
            "status": "failed_after_all_cycles",
            "code": inner_result["code"],
            "outer_cycles": CONFIG.OUTER_MAX_CYCLES,
            "memory": memory.to_serializable(),
        }

    try:
        result = _run_with_global_timeout(_core, CONFIG.GLOBAL_TIMEOUT_SECONDS)
    except PipelineTimeoutError as e:
        result = {"status": "pipeline_timeout", "error": str(e), "memory": memory.to_serializable()}

    _log_run(query, result)
    return result


def main():
    print("=" * 60)
    #print(f"🔧 MOTOR MASPY MULTI-AGENTE (V5.1 - PREVENÇÃO DE AMNÉSIA DE CONTEXTO)")
    #print("=" * 60)

    # 1. Instanciamos o LLM Gerador (Rápido, criativo)
    llm_gerador = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
    
    # 2. Instanciamos o LLM Revisor (Lógico, rigoroso, idealmente um modelo mais pesado)
    # Reaproveitado também como Corretor no loop interno de self-debugging.
    llm_revisor = ChatOllama(model=REVISOR_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.0)
    
    emb = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
    vs = Chroma(collection_name="maspy_codes", embedding_function=emb, persist_directory=EMBEDDING_DIR)
    retriever = MaspyEntityRetriever(vectorstore=vs, search_kwargs={"k": 3})

    while True:
        query = input("\n[MASPY] > ").strip()
        if not query or query.lower() in ["sair", "exit"]: break
        
        start_time = time.time()
        global stop_spinner
        
        try:
            docs = retriever.invoke(query)
            context = "\n\n".join([d.page_content for d in docs])

            stop_spinner = False
            threading.Thread(target=_spinner, daemon=True).start()

            result = processar_query_com_self_debugging(query, context, llm_gerador, llm_revisor)

            stop_spinner = True
            time.sleep(0.2)

            print(f"\n{'='*60}")
            if result["status"] == "validated":
                print(f"💡 CÓDIGO MASPY FINAL (validado no sandbox):\n")
                print(result["code"])
                print(f"{'='*60}\n✅ Ciclos externos: {result['outer_cycles']} | Tentativas internas: {result['inner_attempts']}")
            elif result["status"] == "pipeline_timeout":
                print(f"⏱️  Consulta excedeu o tempo limite global ({CONFIG.GLOBAL_TIMEOUT_SECONDS}s).")
                print(f"Possível loop de percepção/ação sem terminação em algum ciclo. Veja o log para detalhes.")
            else:
                print(f"⚠️  Não foi possível validar o código após {result['outer_cycles']} ciclo(s) externo(s).")
                print(f"Último código gerado (NÃO validado):\n")
                print(result["code"])

            print(f"{'='*60}\n⏱️  Tempo de processamento: {time.time()-start_time:.2f}s")

        except Exception as e:
            stop_spinner = True
            print(f"\n❌ Erro na geração: {e}")

if __name__ == "__main__":
    main()