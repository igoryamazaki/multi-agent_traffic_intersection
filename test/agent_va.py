# ============================================================
# agent_va.py - Agente VA (Veículo Autônomo / AV-agent)
#
# Conforme Fig. 1 e Fig. 3 do artigo ADFERS:
# - Percebe o ambiente via sensores (para condução)
# - Age no ambiente via atuadores (frear, desviar, seguir)
# - NÃO detecta conflitos éticos (isso é do Agente Ético)
# - Recebe recomendações do Ético via ECP (Contract Net)
# - Processa recomendações: Q3 (aceitar?) e Q4 (pedir info?)
#
# Contract Net: VA é o GERENTE (manager/decisor).
#   Fase 3 (Decisão): VA recebe proposta → avalia → responde
# ============================================================

from maspy import *
from utilities import HashableDict


class AgenteVA(Agent):
    """
    AV-agent: conduz o veículo e decide sobre recomendações éticas.

    Crenças iniciais: conduzindo, velocidade, localizacao
    Objetivo inicial: conduzir
    """

    def __init__(self, agt_name):
        super().__init__(agt_name)
        # ---- Crenças iniciais ----
        self.add(Belief("conduzindo", 1))
        self.add(Belief("velocidade", 60))
        self.add(Belief("localizacao", "na_via"))
        # ---- Objetivo inicial: conduzir ----
        self.add(Goal("conduzir"))

    # ============================================================
    # PLANO 1: Conduzir (monitorar ambiente para condução)
    # Gatilho: gain Goal("conduzir")
    # Contexto: Belief("conduzindo", Status)
    #
    # O VA percebe o ambiente para condução (semáforo, via livre).
    # NÃO detecta conflitos éticos. Apenas conduz normalmente.
    # O Agente Ético é quem monitora conflitos éticos.
    # ============================================================
    @pl(gain, Goal("conduzir"), Belief("conduzindo", Any))
    def iniciar_conducao(self, src, status):
        self.print("Conduzindo veículo autônomo...")

        # Percebe o ambiente (sensores de condução)
        perc_semaforo = self.get(Belief("semaforo_aberto", Any, "Cruzamento"))
        semaforo = perc_semaforo.values if perc_semaforo else 0

        self.print(f"Percepção de condução: semaforo={'verde' if semaforo else 'vermelho'}")

        # Atualiza localização
        if self.has(Belief("localizacao", "na_via")):
            self.rm(Belief("localizacao", "na_via"))
            self.add(Belief("localizacao", "no_cruzamento"))
            self.print("VA chegou ao cruzamento.")

        # VA está conduzindo normalmente.
        # Se o Agente Ético detectar conflito ético, ele enviará
        # uma recomendação via ECP (Contract Net). O VA aguarda.
        self.print("Aguardando recomendações do Agente Ético...")

    # ============================================================
    # PLANO 2: Processar recomendação do Agente Ético
    # Gatilho: gain Belief("sugestao_manobra_segura", Recomendacao)
    # Contexto: Belief("conduzindo", Status)
    #
    # ==== CONTRACT NET - FASE 3 (Decisão) ====
    # VA recebe proposta ECP do Ético e avalia (Fig. 3):
    #   Q3: Recomendação é coerente com percepções e regras do VA?
    #     Sim → executa ação
    #     Não → Q4: Situação é perigosa (pedestre/veículo)?
    #       Sim → envia ECP(AV, ET, RJ-1, ?, ?) pedindo detalhes ao Ético
    #       Não → dismiss recommendation (decisão autônoma)
    # ============================================================
    @pl(gain, Belief("sugestao_manobra_segura", Any),
         Belief("conduzindo", Any))
    def avaliar_proposta_etica(self, src, recomendacao, status):
        acao    = recomendacao.get("acao", "frear")
        origem  = recomendacao.get("origem", "AgenteEtico")
        conflito = recomendacao.get("conflito", HashableDict())

        self.print(f"Contract Net Fase 3 - Proposta recebida de {src}:")
        self.print(f"  ECP: Ação={acao}, Origem={origem}")

        # Decisão humana (EG 19): aceita sempre, sem questionar
        if origem == "HITL":
            self.print("Q3: Sim - Origem HITL, decisão humana aceita diretamente")
            self.add(Belief("conflito_pendente", conflito))
            self.add(Goal("aceitar_sugestao", ((acao, recomendacao),)))
            return

        # Lê percepções atuais do ambiente (regras de trânsito do VA)
        p_semaforo  = self.get(Belief("semaforo_aberto",    Any, "Cruzamento"))
        p_pedestre  = self.get(Belief("pedestre_detectado", Any, "Cruzamento"))
        p_obstaculo = self.get(Belief("obstaculo",          Any, "Cruzamento"))
        p_veiculo   = self.get(Belief("veiculo_detectado",  Any, "Cruzamento"))
        p_v_lateral = self.get(Belief("veiculo_lateral",    Any, "Cruzamento"))

        semaforo   = p_semaforo.values  if p_semaforo  else 0
        pedestre   = p_pedestre.values  if p_pedestre  else 0
        obstaculo  = p_obstaculo.values if p_obstaculo else 0
        veiculo    = p_veiculo.values   if p_veiculo   else 0
        v_lateral  = p_v_lateral.values if p_v_lateral else 0

        self.print(f"  Percepções VA: semaforo={semaforo}, pedestre={pedestre}, "
                   f"obstaculo={obstaculo}, veiculo={veiculo}, veiculo_lateral={v_lateral}")

        # Q3: A recomendação é coerente com o que o VA percebe?
        # Regras:
        #   frear   → coerente se há pedestre, veículo, obstáculo ou sinal fechado
        #   desviar → coerente se há obstáculo, sem pedestre, sem veículo (frontal ou lateral)
        #             veiculo_lateral bloqueia desvio → Q3=Não → Q4
        #   seguir  → coerente se sinal aberto e sem obstáculos/pedestres/veículos
        if acao == "frear":
            q3 = bool(pedestre or veiculo or obstaculo or not semaforo)
        elif acao == "desviar":
            q3 = bool(obstaculo and not pedestre and not veiculo and not v_lateral)
        elif acao == "seguir":
            q3 = bool(semaforo and not pedestre and not veiculo and not obstaculo)
        else:
            q3 = False

        if q3:
            self.print(f"Q3: Sim - '{acao}' é coerente com as percepções do VA")
            self.add(Belief("conflito_pendente", conflito))
            self.add(Goal("aceitar_sugestao", ((acao, recomendacao),)))
        else:
            # Q4: situação tem perigo real que impede executar a recomendação?
            # Inclui veiculo_lateral pois bloqueia desvio com risco de colisão
            situacao_perigosa = bool(pedestre or veiculo or v_lateral)
            if situacao_perigosa:
                self.print(f"Q3: Não - '{acao}' conflita com percepções. "
                           f"Q4: Sim - Situação perigosa, pedindo alternativa ao Ético")
                self.print(f"  ECP(AV, ET, Cruzamento, ?, ?)")
                self.add(Belief("conflito_pendente", conflito))
                self.add(Belief("recomendacao_pendente", recomendacao))
                self.add(Goal("pedir_detalhes", conflito))
            else:
                self.print(f"Q3: Não - '{acao}' conflita com percepções. "
                           f"Q4: Não - Sem perigo imediato, VA decide autonomamente")
                self.add(Goal("decisao_autonoma", conflito))

    # ============================================================
    # PLANO 3: Aceitar sugestão e executar ação
    # Gatilho: gain Goal("aceitar_sugestao", Dados)
    # Contexto: Belief("conduzindo", Status)
    #
    # Fig. 3: Q3=Sim → "execute actions"
    # ============================================================
    @pl(gain, Goal("aceitar_sugestao", Any), Belief("conduzindo", Any))
    def executar_acao_recomendada(self, src, dados, status):
        acao, recomendacao = dados
        self.print(f"Executando ação recomendada: {acao}")

        # Atuador: executa movimento no ambiente
        self.executar_movimento(acao)

        # Remove conflito pendente
        conflito = recomendacao.get("conflito", HashableDict())
        if self.has(Belief("conflito_pendente", conflito)):
            self.rm(Belief("conflito_pendente", conflito))

        # Log para HITL
        log_entry = HashableDict({
            "tipo": "sugestao_aceita",
            "agente": self.my_name,
            "acao": acao,
            "conflito": conflito,
            "origem": recomendacao.get("origem", "AgenteEtico"),
        })
        self.send("HITL", tell, Belief("log_evento", log_entry), "AgentComm")

        self.print(f"Ação '{acao}' executada com sucesso!")
        self.stop_cycle()

    # ============================================================
    # PLANO 4: Pedir mais detalhes ao Ético (Q4 = Sim)
    # Gatilho: gain Goal("pedir_detalhes", Conflito)
    # Contexto: nenhum
    #
    # Fig. 3: Q4 → ask → send message → Ethical Agent
    # ECP(AV, ET, RJ-1, ?, ?) - pede conjunto diferente de ações
    # ============================================================
    @pl(gain, Goal("pedir_detalhes", Any))
    def consultar_etico(self, src, conflito):
        self.print(f"Pedindo mais detalhes ao Agente Ético")

        pedido = HashableDict({"conflito": conflito, "solicitante": self.my_name})
        self.send(
            "AgenteEtico", achieve,
            Goal("fornecer_detalhes", pedido),
            "AgentComm"
        )

    # ============================================================
    # PLANO 5: Processar detalhes recebidos do Ético
    # Gatilho: gain Belief("detalhes_eticos", Detalhes)
    # Contexto: Belief("recomendacao_pendente", RecPendente)
    #
    # Fig. 3: "returns to step 1" com nova informação → aceita
    # ============================================================
    @pl(gain, Belief("detalhes_eticos", Any),
         Belief("recomendacao_pendente", Any))
    def aceitar_alternativa(self, src, detalhes, rec_pendente):
        self.print(f"Detalhes recebidos do Agente Ético")

        acao = detalhes.get("recomendacao_original", "frear")
        self.print(f"Com mais detalhes, aceitando ação: {acao}")
        self.add(Goal("aceitar_sugestao", ((acao, rec_pendente),)))

    # ============================================================
    # PLANO 6: Decisão autônoma (dismiss recommendation)
    # Gatilho: gain Goal("decisao_autonoma", Conflito)
    # Contexto: Belief("conduzindo", Status)
    #
    # Fig. 3: "dismiss recommendation" → VA decide sozinho
    # ============================================================
    @pl(gain, Goal("decisao_autonoma", Any), Belief("conduzindo", Any))
    def descartar_e_decidir(self, src, conflito, status):
        self.print(f"Decisão autônoma para: {conflito}")

        if conflito.get("tipo") == "pedestre":
            acao = "frear"
        else:
            acao = "frear"

        self.print(f"Decisão autônoma: {acao}")
        self.executar_movimento(acao)

        log_entry = HashableDict({
            "tipo": "decisao_autonoma",
            "agente": self.my_name,
            "acao": acao,
            "conflito": conflito,
            "motivo": "recomendacao_rejeitada",
        })
        self.send("HITL", tell, Belief("log_evento", log_entry), "AgentComm")
        self.stop_cycle()

    # ============================================================
    # PLANO 7: Aguardar HITL (dilema ético → handover)
    # Gatilho: gain Belief("aguardar_hitl", Info)
    # Contexto: nenhum
    #
    # EG 19: "safe condition" / handover routines
    # ============================================================
    @pl(gain, Belief("aguardar_hitl", Any))
    def entrar_em_modo_seguro(self, src, info):
        self.print("DILEMA ÉTICO! Aguardando decisão do HITL...")
        self.print(f"Info: {info.get('mensagem', '')}")

        # Modo seguro: handover (EG 19)
        if self.has(Belief("velocidade")):
            self.rm(Belief("velocidade"))
        self.add(Belief("velocidade", 0))
        self.print("VA em modo seguro - velocidade = 0 (handover)")
