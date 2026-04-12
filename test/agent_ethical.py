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
    ConflitoGaltung,
    criar_conflito_pedestre,
    criar_conflito_dilema,
    criar_conflito_obstaculo,
    criar_conflito_veiculo,
    criar_conflito_pedestre_zona_escolar,
)

# ============================================================
# Percepções usadas pelo Agente Ético:
#   semaforo_aberto      - sinal verde (1) ou vermelho (0)
#   pedestre_detectado   - pedestre na faixa (1=sim)
#   obstaculo            - objeto na via (1=sim)
#   veiculo_detectado    - veículo frontal (1=sim)
#   veiculo_atras        - carro atrás do VA (1=sim) → dilema Exemplo 1
#   veiculo_lateral      - carro ao lado do VA (1=sim) → cenário Q4
#   zona_escolar         - VA em zona escolar (1=sim) → MODD (transfer) se sinal aberto
# ============================================================


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
        # ---- MODD: Moral Operational Design Domain (Rakow et al. EUMAS 2024, Seção 4.2) ----
        # Define contextos de resolução autônoma (resolve) vs. transferência ao HITL (transfer).
        # threshold_minimo: diferença mínima de utilidade para decisão autônoma confiável.
        # Nota: "pedestre_veiculo_atras" (dilema genuíno) NÃO consta no MODD porque
        # eh_dilema=True → Q1=Não dispara primeiro, escalando ao HITL antes de o MODD
        # ser consultado. Dilemas verdadeiros (u_i=u_j) são tratados pelo fluxo Q1/Q2,
        # não pelo MODD (Def. 2.2, NB2). O MODD trata incerteza de decisão, não empate.
        self.modd = {
            "pedestre":              {"resolver_autonomo": True, "threshold_minimo": 1.0, "autoridade": "AgenteEtico", "prioridade": "proteger_pedestre",    "justificativa": "EG 2"},
            # threshold=4.0: sinal aberto → diff=3.0 < 4.0 → (transfer); fechado → diff=4.0 → (resolve)
            "pedestre_zona_escolar": {"resolver_autonomo": True, "threshold_minimo": 4.0, "autoridade": "HITL",        "prioridade": "alta_vigilancia",      "justificativa": "EG 2 + zona escolar"},
            "obstaculo":             {"resolver_autonomo": True, "threshold_minimo": 0.5, "autoridade": "AgenteEtico", "prioridade": "evitar_obstaculo",     "justificativa": "EG 5"},
            "veiculo":               {"resolver_autonomo": True, "threshold_minimo": 1.0, "autoridade": "AgenteEtico", "prioridade": "evitar_colisao",       "justificativa": "EG 7"},
            "_default":              {"resolver_autonomo": False, "threshold_minimo": float("inf"), "autoridade": "HITL", "prioridade": "seguranca_maxima", "justificativa": "tipo desconhecido"},
        }

    # ============================================================
    # MODD: Moral Operational Design Domain
    # Rakow et al. EUMAS 2024, Seção 4.2
    # ============================================================

    def consultar_modd(self, tipo):
        """Retorna regra MODD para o tipo de conflito."""
        return self.modd.get(tipo, self.modd["_default"])

    def modd_pode_resolver(self, tipo, diferenca):
        """(resolve): True se MODD autoriza resolução autônoma.
        Condição: resolver_autonomo=True E diferenca >= threshold_minimo."""
        regra = self.consultar_modd(tipo)
        return regra["resolver_autonomo"] and diferenca >= regra["threshold_minimo"]

    def modd_explicar(self, tipo, diferenca):
        """Retorna string de auditoria MODD para log."""
        regra = self.consultar_modd(tipo)
        pode = self.modd_pode_resolver(tipo, diferenca)
        modo = "(resolve)" if pode else "(transfer)"
        return (
            f"MODD {modo} | tipo={tipo} | diff={diferenca:.2f} "
            f"threshold={regra['threshold_minimo']} | "
            f"autoridade={regra['autoridade']} | {regra['justificativa']}"
        )

    # ============================================================
    # PLANO 1: Monitorar o ambiente urbano
    # Gatilho: gain Goal("monitorar_ambiente")
    # Contexto: Belief("status_etico", Status)
    #
    # Fig. 1: Ético percebe ambiente via sensores.
    # Fig. 2: Percepts → Beliefs → Plan & Utility selection
    # ============================================================
    @pl(gain, Goal("monitorar_ambiente"), Belief("status_etico", Any))
    def perceber_e_classificar_conflito(self, src, status):
        self.print("Monitorando ambiente urbano (sensores)...")

        # Percebe o ambiente
        perc_semaforo     = self.get(Belief("semaforo_aberto",    Any, "Cruzamento"))
        perc_pedestre     = self.get(Belief("pedestre_detectado", Any, "Cruzamento"))
        perc_obstaculo    = self.get(Belief("obstaculo",          Any, "Cruzamento"))
        perc_veiculo      = self.get(Belief("veiculo_detectado",  Any, "Cruzamento"))
        perc_v_atras      = self.get(Belief("veiculo_atras",      Any, "Cruzamento"))
        perc_v_lateral    = self.get(Belief("veiculo_lateral",    Any, "Cruzamento"))
        perc_zona_escolar = self.get(Belief("zona_escolar",       Any, "Cruzamento"))

        semaforo     = perc_semaforo.values     if perc_semaforo     else 0
        pedestre     = perc_pedestre.values     if perc_pedestre     else 0
        obstaculo    = perc_obstaculo.values    if perc_obstaculo    else 0
        veiculo      = perc_veiculo.values      if perc_veiculo      else 0
        v_atras      = perc_v_atras.values      if perc_v_atras      else 0
        v_lateral    = perc_v_lateral.values    if perc_v_lateral    else 0
        zona_escolar = perc_zona_escolar.values if perc_zona_escolar else 0

        self.print(f"Percepções: semaforo={semaforo}, pedestre={pedestre}, "
                   f"obstaculo={obstaculo}, veiculo={veiculo}, "
                   f"veiculo_atras={v_atras}, veiculo_lateral={v_lateral}, "
                   f"zona_escolar={zona_escolar}")

        # ---- Detecta e classifica conflito ético ----
        conflito_detectado = False
        conflito = HashableDict()

        if pedestre and v_atras:
            # Exemplo 1 do artigo: DILEMA ÉTICO
            # Frear → protege pedestre (ru_safe=10)
            # Seguir → protege passageiro de colisão traseira (av_pass_safe=10)
            # u_i = u_j = 10 → Q1=Não → Q2=Não → HITL (EG 8)
            conflito_detectado = True
            conflito = criar_conflito_dilema(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral)
            self.print("CONFLITO ÉTICO DETECTADO: Pedestre + veiculo atrás (DILEMA - Exemplo 1)!")

        elif pedestre and zona_escolar:
            # Cenário MODD (transfer): pedestre em zona escolar
            # MODD threshold=4.0: sinal aberto → diff=3.0 < 4.0 → (transfer) → HITL
            #                     sinal fechado → diff=4.0 ≥ 4.0 → (resolve) → VA executa
            conflito_detectado = True
            conflito = criar_conflito_pedestre_zona_escolar(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral)
            self.print("CONFLITO ÉTICO DETECTADO: Pedestre em zona escolar (MODD threshold elevado)!")

        elif pedestre:
            # Exemplo 2 do artigo: pedestre, sem carro atrás
            # u_frear=10 (ru_safe), u_seguir=9 (av_respects_rule) → Q1=Sim
            conflito_detectado = True
            conflito = criar_conflito_pedestre(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral)
            self.print("CONFLITO ÉTICO DETECTADO: Pedestre no cruzamento (Exemplo 2)!")

        elif obstaculo and v_lateral:
            # Cenário Q4: obstáculo + veículo lateral
            # Ético recomenda "desviar" (obstáculo) mas VA percebe veiculo_lateral
            # → VA: Q3=Não (desviar+veiculo) → Q4=Sim → pede alternativa ao Ético
            conflito_detectado = True
            conflito = criar_conflito_obstaculo(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral)
            self.print("CONFLITO ÉTICO DETECTADO: Obstáculo + veiculo lateral (cenario Q4)!")

        elif veiculo:
            conflito_detectado = True
            conflito = criar_conflito_veiculo(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral)
            self.print("CONFLITO ÉTICO DETECTADO: Veiculo no cruzamento!")

        elif obstaculo:
            conflito_detectado = True
            conflito = criar_conflito_obstaculo(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral)
            self.print("CONFLITO ÉTICO DETECTADO: Obstáculo na via!")

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
    def calcular_utilidades_e_decidir(self, src, conflito, c):
        self.print(f"Avaliando conflito: {conflito}")

        # Calcula utilidades (Def. 2.1)
        acao, utilidade, eh_dilema = selecionar_melhor_acao(conflito)
        relatorio = gerar_relatorio_utilidades(conflito)

        self.print(f"Utilidades: {relatorio['utilidades']}")
        self.print(f"Ação recomendada: {acao} (utilidade: {utilidade})")

        # Log Triângulo de Galtung (Seção 4.3: ATA explica conflito à autoridade)
        if isinstance(conflito, ConflitoGaltung):
            self.print(conflito.explicar())

        # Q1: Existe utilidade maximizada? (Fig. 2)
        if not eh_dilema:
            self.print("Q1: Sim - Utilidade maximizada encontrada")
            # MODD: (resolve) ou (transfer)? (Seção 4.2)
            utilidades_vals = sorted(relatorio["utilidades"].values(), reverse=True)
            diferenca = utilidades_vals[0] - utilidades_vals[1] if len(utilidades_vals) >= 2 else float("inf")
            tipo = conflito.get("tipo", "_default")
            self.print(self.modd_explicar(tipo, diferenca))

            if self.modd_pode_resolver(tipo, diferenca):
                # MODD (resolve) → envia recomendação ao VA
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
                # MODD (transfer) → escala ao HITL mesmo com Q1=Sim
                self.print("MODD (transfer): threshold não atingido → Escalar para HITL")
                self.add(Goal("escalar_para_hitl", ((conflito, relatorio),)))
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
    def propor_acao_ao_va(self, src, recomendacao):
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
    def acionar_intervencao_humana(self, src, dados, conflito):
        conflito_info, relatorio = dados

        self.print(f"ECP(ET, HITL, {conflito_info.get('posicao')}, "
                   f"{{handover, retake control}}, {relatorio['utilidades']})")

        # Envia dilema ao HITL
        if relatorio.get("eh_dilema"):
            mensagem = "Utilidades iguais - decisão humana necessária"
        else:
            mensagem = "MODD (transfer): threshold de confiança não atingido - decisão humana necessária"
        dilema_info = HashableDict({
            "tipo": "dilema_etico",
            "conflito": conflito_info,
            "relatorio": relatorio,
            "mensagem": mensagem,
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
    def responder_consulta_do_va(self, src, pedido):
        conflito = pedido.get("conflito", {})
        self.print(f"VA pediu detalhes. Recalculando para: {conflito}")

        relatorio = gerar_relatorio_utilidades(conflito)

        # Se há veiculo_lateral, desviar está bloqueado → alternativa é frear
        # Fig. 3: Ético provê conjunto alternativo de ações ao VA
        if conflito.get("veiculo_lateral"):
            self.print("  veiculo_lateral detectado → alternativa: frear (desviar bloqueado)")
            acao_alternativa = "frear"
        else:
            acao_alternativa = relatorio["acao_recomendada"]

        detalhes = HashableDict({
            "tipo": "detalhes_completos",
            "relatorio": relatorio,
            "todas_opcoes": relatorio["utilidades"],
            "recomendacao_original": acao_alternativa,
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
    def repassar_decisao_humana(self, src, instrucao):
        self.print(f"Instrução do HITL: {instrucao}")

        recomendacao = HashableDict({
            "acao": instrucao.get("acao", "frear"),
            "utilidade": 10.0,
            "conflito": instrucao.get("conflito", HashableDict()),
            "origem": "HITL",
        })

        self.send("VA", tell, Belief("sugestao_manobra_segura", recomendacao), "AgentComm")
        self.print(f"Instrução do HITL repassada ao VA: {recomendacao['acao']}")
