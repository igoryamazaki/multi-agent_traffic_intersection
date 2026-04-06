# ============================================================
# agent_hitl.py - Agente HITL (Human-in-the-Loop)
#
# Conforme Fig. 1 do artigo ADFERS:
# - Recebe logs de todos os agentes (observador)
# - Investiga dilemas éticos escalados pelo Ético (interventor)
# - Toma decisão humana (EG 8: genuine dilemmatic situations)
# - Envia instrução de volta ao Ético → VA (EG 19: handover)
# ============================================================

from maspy import *
from utilities import HashableDict


class AgenteHITL(Agent):

    def __init__(self, agt_name):
        super().__init__(agt_name)
        # ---- Crenças iniciais ----
        self.add(Belief("status", "observando"))
        self.add(Belief("total_logs", 0))
        self._log_count = 0
        self._logs = []

    # ============================================================
    # PLANO 1: Registrar log de evento
    # Gatilho: gain Belief("log_evento", Evento)
    # Contexto: nenhum
    # ============================================================
    @pl(gain, Belief("log_evento", Any))
    def auditar_evento(self, src, evento):
        self._log_count += 1
        self._logs.append({"id": self._log_count, "src": str(src), "evento": evento})

        tipo = evento.get("tipo", "desconhecido")
        self.print(f"[LOG #{self._log_count}] De: {src} | Tipo: {tipo}")
        self.print(f"  Detalhes: {evento}")

        if self.has(Belief("total_logs")):
            self.rm(Belief("total_logs"))
        self.add(Belief("total_logs", self._log_count))

        if tipo == "decisao_autonoma":
            self.print(f"  ALERTA: VA tomou decisão autônoma!")
            self.add(Belief("alerta_decisao_autonoma", evento))

    # ============================================================
    # PLANO 2: Investigar dilema ético
    # Gatilho: gain Goal("investigar_dilema", Info)
    # Contexto: nenhum
    #
    # EG 8: genuine dilemmatic situations → decisão humana
    # EG 19: handover routines
    # ============================================================
    @pl(gain, Goal("investigar_dilema", Any))
    def tomar_decisao_humana(self, src, info):
        self.print("=" * 50)
        self.print("DILEMA ETICO RECEBIDO - Investigação iniciada")
        self.print("=" * 50)
        self.print(f"Recebido de: {src}")
        self.print(f"Conflito: {info.get('conflito', {})}")
        self.print(f"Mensagem: {info.get('mensagem', '')}")

        relatorio = info.get("relatorio", {})
        utilidades = relatorio.get("utilidades", {})
        self.print(f"Utilidades: {utilidades}")

        self._log_count += 1
        self._logs.append({
            "id": self._log_count, "src": str(src),
            "evento": {"tipo": "dilema_etico", "info": info}
        })

        # Decisão humana (simulada)
        conflito = info.get("conflito", {})
        decisao = self._tomar_decisao_humana(conflito, utilidades)

        self.print(f"Decisão do HITL: {decisao}")

        # Envia instrução ao Ético → Ético repassa ao VA
        instrucao = HashableDict({
            "acao": decisao,
            "conflito": conflito,
            "decidido_por": "HITL",
        })
        self.send(
            "AgenteEtico", achieve,
            Goal("executar_instrucao_hitl", instrucao),
            "AgentComm"
        )
        self.print("Instrução enviada ao Agente Ético.")
        self.print("=" * 50)

    # ============================================================
    # PLANO 3: Processar alerta de decisão autônoma
    # Gatilho: gain Belief("alerta_decisao_autonoma", Evento)
    # Contexto: nenhum
    # ============================================================
    @pl(gain, Belief("alerta_decisao_autonoma", Any))
    def registrar_decisao_autonoma(self, src, evento):
        self.print("ALERTA: VA tomou decisão sem aceitar recomendação")
        self.print(f"Ação: {evento.get('acao', '?')}")
        self.add(Belief("pendencia_investigacao", evento))

    # ============================================================
    # Método auxiliar: simula decisão humana
    # EG 7: proteção de vida humana é prioridade máxima
    # ============================================================
    def _tomar_decisao_humana(self, conflito, utilidades):
        tipo = conflito.get("tipo", "desconhecido")
        if tipo == "pedestre":
            self.print("HITL: Pedestre → FREAR (EG 7: vida humana)")
            return "frear"
        elif tipo == "veiculo":
            self.print("HITL: Veículo → FREAR (segurança)")
            return "frear"
        else:
            self.print("HITL: Obstáculo → DESVIAR")
            return "desviar"
