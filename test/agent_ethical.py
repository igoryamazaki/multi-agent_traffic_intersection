# ============================================================
# agent_ethical.py - Agente Ético (Ethical Agent)
#
# Conforme Fig. 1 e Fig. 2 do artigo ADFERS:
# - Monitora o ambiente urbano via sensores
# - Detecta conflitos éticos em cruzamentos
# - Calcula utilidades éticas (Def. 2.1, utilitarismo)
# - Envia recomendações ao VA via ECP dentro do Contract Net
# - Escala dilemas éticos para o HITL
#
# Governor module: único componente com raciocínio ético.
#
# Contract Net: Ético é o PARTICIPANTE que envia propostas.
#   Fase 1 (CFP): Ético detecta conflito → envia ECP ao VA
#   Fase 2 (Proposta): Ético envia recomendação com utilidades
# ECP := (Sender, Receiver, Env_pos, Act, Utl) - Def. 3.1
# ============================================================

from maspy import *
from utilities import (
    selecionar_melhor_acao,
    gerar_relatorio_utilidades,
    HashableDict,
)


class AgenteEtico(Agent):
    """
    EA := (Ute, Be, Rr, Pl, Act, Utl) - Definição 2.2
    """

    def __init__(self, agt_name):
        super().__init__(agt_name)
        # ---- Crenças iniciais ----
        self.add(Belief("status_etico", "monitorando"))
        self.add(Belief("sem_conflito_ativo"))
        # ---- Objetivo inicial: monitorar ambiente (Fig. 1) ----
        self.add(Goal("monitorar_ambiente"))

    # ============================================================
    # PLANO 1: Monitorar o ambiente urbano
    # Gatilho: gain Goal("monitorar_ambiente")
    # Contexto: Belief("status_etico", Status)
    #
    # Fig. 1: Ético percebe ambiente via sensores.
    # Fig. 2: Percepts → Beliefs → Plan & Utility selection
    # ============================================================
    @pl(gain, Goal("monitorar_ambiente"), Belief("status_etico", Any))
    def monitorar_ambiente(self, src, status):
        self.print("Monitorando ambiente urbano (sensores)...")

        # Percebe o ambiente
        perc_semaforo = self.get(Belief("semaforo_aberto", Any, "Cruzamento"))
        perc_pedestre = self.get(Belief("pedestre_detectado", Any, "Cruzamento"))
        perc_obstaculo = self.get(Belief("obstaculo", Any, "Cruzamento"))
        perc_veiculo = self.get(Belief("veiculo_detectado", Any, "Cruzamento"))

        semaforo = perc_semaforo.values if perc_semaforo else 0
        pedestre = perc_pedestre.values if perc_pedestre else 0
        obstaculo = perc_obstaculo.values if perc_obstaculo else 0
        veiculo = perc_veiculo.values if perc_veiculo else 0

        self.print(f"Percepções: semaforo={semaforo}, pedestre={pedestre}, "
                   f"obstaculo={obstaculo}, veiculo={veiculo}")

        # Detecta conflito ético
        conflito_detectado = False
        conflito = HashableDict()

        if pedestre:
            conflito_detectado = True
            conflito = HashableDict({
                "tipo": "pedestre",
                "semaforo": "aberto" if semaforo else "fechado",
                "posicao": "Cruzamento",
                "veiculo_atras": 1 if veiculo else 0,
            })
            self.print(f"CONFLITO ÉTICO DETECTADO: Pedestre no cruzamento!")

        elif veiculo:
            conflito_detectado = True
            conflito = HashableDict({
                "tipo": "veiculo",
                "semaforo": "aberto" if semaforo else "fechado",
                "posicao": "Cruzamento",
            })
            self.print(f"CONFLITO ÉTICO DETECTADO: Veículo no cruzamento!")

        elif obstaculo:
            conflito_detectado = True
            conflito = HashableDict({
                "tipo": "obstaculo",
                "semaforo": "aberto" if semaforo else "fechado",
                "posicao": "Cruzamento",
            })
            self.print(f"CONFLITO ÉTICO DETECTADO: Obstáculo na via!")

        if conflito_detectado:
            if self.has(Belief("sem_conflito_ativo")):
                self.rm(Belief("sem_conflito_ativo"))
            self.add(Belief("conflito_ativo", conflito))
            # Inicia raciocínio ético (Fig. 2: Plan & Utility selection)
            self.add(Goal("avaliar_conflito", conflito))
        else:
            self.print("Nenhum conflito ético. Ambiente seguro.")
            self.stop_cycle()

    # ============================================================
    # PLANO 2: Avaliar conflito e calcular utilidades
    # Gatilho: gain Goal("avaliar_conflito", Conflito)
    # Contexto: Belief("conflito_ativo", C)
    #
    # Fig. 2: Plan & Utility selection → Q1 → Q2
    # Contract Net Fase 1: gera proposta (CFP com recomendação)
    # ============================================================
    @pl(gain, Goal("avaliar_conflito", Any), Belief("conflito_ativo", Any))
    def avaliar_conflito(self, src, conflito, c):
        self.print(f"Avaliando conflito: {conflito}")

        # Calcula utilidades (Def. 2.1)
        acao, utilidade, eh_dilema = selecionar_melhor_acao(conflito)
        relatorio = gerar_relatorio_utilidades(conflito)

        self.print(f"Utilidades: {relatorio['utilidades']}")
        self.print(f"Ação recomendada: {acao} (utilidade: {utilidade})")

        # Q1: Existe utilidade maximizada? (Fig. 2)
        if not eh_dilema:
            # Q1 = Sim → Envia recomendação ao VA
            self.print("Q1: Sim - Utilidade maximizada encontrada")
            recomendacao = HashableDict({
                "acao": acao,
                "utilidade": utilidade,
                "conflito": conflito,
                "origem": "AgenteEtico",
                "posicao": conflito.get("posicao", "Cruzamento"),
                "utilidades_usadas": relatorio["utilidades"],
            })
            self.add(Goal("enviar_recomendacao", recomendacao))
        else:
            # Q1 = Não → Q2: Tentar outro plano?
            self.print("Q1: Não - Utilidades iguais (DILEMA ÉTICO)")
            self.print("Q2: Não - Sem plano alternativo → Escalar para HITL")
            self.add(Goal("escalar_para_hitl", ((conflito, relatorio),)))

    # ============================================================
    # PLANO 3: Enviar recomendação ao VA via ECP (Contract Net)
    # Gatilho: gain Goal("enviar_recomendacao", Recomendacao)
    # Contexto: nenhum
    #
    # Contract Net Fase 2 (Proposta):
    # ECP(Sender=ET, Receiver=AV, Env_pos, Act, Utl)
    # Conforme Exemplo 2: ECP(ET, AV, RJ-2, {hit the brakes}, {u_i})
    # ============================================================
    @pl(gain, Goal("enviar_recomendacao", Any))
    def enviar_recomendacao(self, src, recomendacao):
        acao = recomendacao["acao"]
        utilidade = recomendacao["utilidade"]
        posicao = recomendacao.get("posicao", "Cruzamento")

        # Formato ECP (Def. 3.1)
        self.print(f"Contract Net Fase 2 - Enviando proposta (ECP):")
        self.print(f"  ECP(ET, AV, {posicao}, {{{acao}}}, {{{utilidade}}})")

        # Envia via tell (Fig. 2: send recommendation → tell → AV-agent)
        self.send(
            "VA", tell,
            Belief("sugestao_manobra_segura", recomendacao),
            "AgentComm"
        )

        # Log para HITL
        log_entry = HashableDict({
            "tipo": "recomendacao_enviada",
            "de": self.my_name, "para": "VA",
            "acao": acao, "utilidade": utilidade,
        })
        self.send("HITL", tell, Belief("log_evento", log_entry), "AgentComm")

        self.add(Belief("sem_conflito_ativo"))

    # ============================================================
    # PLANO 4: Escalar dilema ético para o HITL
    # Gatilho: gain Goal("escalar_para_hitl", Dados)
    # Contexto: Belief("conflito_ativo", Conflito)
    #
    # NB2 (Def 2.2): u1 = u2 → handover → HITL
    # Exemplo 1: u_i=10, u_j=10 → DILEMA
    # ECP(ET, HITL, RJ-1, {handover, retake control}, {u_i, u_j})
    # ============================================================
    @pl(gain, Goal("escalar_para_hitl", Any), Belief("conflito_ativo", Any))
    def escalar_para_hitl(self, src, dados, conflito):
        conflito_info, relatorio = dados

        self.print(f"ECP(ET, HITL, {conflito_info.get('posicao')}, "
                   f"{{handover, retake control}}, {relatorio['utilidades']})")

        # Envia dilema ao HITL
        dilema_info = HashableDict({
            "tipo": "dilema_etico",
            "conflito": conflito_info,
            "relatorio": relatorio,
            "mensagem": "Utilidades iguais - decisão humana necessária",
        })
        self.send("HITL", achieve, Goal("investigar_dilema", dilema_info), "AgentComm")

        # Avisa VA para handover (EG 19: safe condition)
        self.send("VA", tell, Belief("aguardar_hitl", dilema_info), "AgentComm")

        self.add(Belief("sem_conflito_ativo"))

    # ============================================================
    # PLANO 5: Fornecer detalhes ao VA (resposta ao Q4)
    # Gatilho: gain Goal("fornecer_detalhes", Pedido)
    # Contexto: nenhum
    #
    # Fig. 3: VA pede mais info → ECP(AV, ET, RJ-1, ?, ?)
    # Ético responde com planos/utilidades alternativos.
    # ============================================================
    @pl(gain, Goal("fornecer_detalhes", Any))
    def fornecer_detalhes(self, src, pedido):
        conflito = pedido.get("conflito", {})
        self.print(f"VA pediu detalhes. Recalculando para: {conflito}")

        relatorio = gerar_relatorio_utilidades(conflito)

        detalhes = HashableDict({
            "tipo": "detalhes_completos",
            "relatorio": relatorio,
            "todas_opcoes": relatorio["utilidades"],
            "recomendacao_original": relatorio["acao_recomendada"],
        })

        self.send(str(src), tell, Belief("detalhes_eticos", detalhes), "AgentComm")

        log_entry = HashableDict({"tipo": "detalhes_fornecidos", "de": self.my_name, "para": str(src)})
        self.send("HITL", tell, Belief("log_evento", log_entry), "AgentComm")

    # ============================================================
    # PLANO 6: Processar instrução do HITL (repasse ao VA)
    # Gatilho: gain Goal("executar_instrucao_hitl", Instrucao)
    # Contexto: nenhum
    # ============================================================
    @pl(gain, Goal("executar_instrucao_hitl", Any))
    def executar_instrucao_hitl(self, src, instrucao):
        self.print(f"Instrução do HITL: {instrucao}")

        recomendacao = HashableDict({
            "acao": instrucao.get("acao", "frear"),
            "utilidade": 10.0,
            "conflito": instrucao.get("conflito", HashableDict()),
            "origem": "HITL",
        })

        self.send("VA", tell, Belief("sugestao_manobra_segura", recomendacao), "AgentComm")
        self.print(f"Instrução do HITL repassada ao VA: {recomendacao['acao']}")
