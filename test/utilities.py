# ============================================================
# utilities.py - Funções de Utilidade Ética (Definição 2.1)
#
# German Ethics Code:
# EG 1: segurança para todos os usuários da via
# EG 2: proteção de indivíduos tem precedência
# EG 5: prevenir acidentes sempre que possível
# EG 7: vida humana é prioridade máxima
# ============================================================

class HashableDict(dict):
    """Dict subclass com __hash__ definido, necessário para valores em Belief/Goal/Percept da MASPY."""
    def __hash__(self):
        def _make_hashable(v):
            if isinstance(v, dict):
                return frozenset((_make_hashable(k), _make_hashable(val)) for k, val in v.items())
            elif isinstance(v, (list, tuple)):
                return tuple(_make_hashable(i) for i in v)
            return v
        return hash(_make_hashable(self))


class ConflitoGaltung(HashableDict):
    """
    Triângulo de Galtung (Rakow et al. EUMAS 2024, Seção 3):
    Formaliza o conflito ético em três vértices:
      V1 = crenças/percepções do ambiente
      V2 = metas incompatíveis entre VA e Ético
      V3 = ações opostas derivadas das metas
    Herda HashableDict para compatibilidade com Belief/Goal da MASPY.
    """
    def __init__(self, dados_adfers, metas_incompativeis, acoes_opostas, crencas):
        super().__init__(dados_adfers)
        self["metas_incompativeis"] = tuple(metas_incompativeis)
        self["acoes_opostas"] = tuple(acoes_opostas)
        self["crencas"] = HashableDict(crencas)

    def explicar(self):
        """Retorna string descritiva dos três vértices para auditoria (Seção 4.3)."""
        v1 = dict(self["crencas"])
        v2 = self["metas_incompativeis"]
        v3 = self["acoes_opostas"]
        return (
            f"Galtung V1(crenças)={v1} | "
            f"V2(metas)={v2} | "
            f"V3(ações)={v3}"
        )


# ---- Constantes de utilidade (Definição 2.1) ----
RU_SAFE = 10              # Usuários da via seguros (EG 1, 2)
AV_PASS_SAFE = 10         # Passageiros do VA seguros (EG 7)
AV_RESPECTS_RULE = 9      # VA respeitou regras de trânsito (EG 5)
AV_DAMAGE = -1             # Dano menor ao VA
TRAFFIC_ENV_DAMAGE = -2    # Dano ao ambiente de trânsito


# ============================================================
# CENÁRIO PADRÃO (Exemplo 2 do artigo):
# Pedestre + semaforo aberto, SEM veiculo_atras
# u_frear=10, u_seguir=9, u_desviar~7  →  Q1=Sim → frear
# ============================================================

_TIPOS_PEDESTRE = ("pedestre", "pedestre_zona_escolar")


def calcular_utilidade_frear(conflito):
    """Utilidade de FREAR. Ex2 do artigo: pedestre → u_i = 10 (ru_safe)."""
    utilidade = 0.0
    if conflito.get("tipo") in _TIPOS_PEDESTRE:
        utilidade += RU_SAFE                    # 10: protege pedestre
    elif conflito.get("tipo") == "veiculo":
        utilidade += AV_PASS_SAFE * 0.8         # 8: evita colisão frontal
    elif conflito.get("tipo") == "obstaculo":
        utilidade += AV_PASS_SAFE * 0.7         # 7: para antes do obstáculo
    if conflito.get("semaforo") == "aberto":
        utilidade += AV_DAMAGE                  # -1: frear no verde = dano menor
    return utilidade


def calcular_utilidade_desviar(conflito):
    """Utilidade de DESVIAR. Protege parcialmente com risco ambiental."""
    utilidade = 0.0
    if conflito.get("tipo") in _TIPOS_PEDESTRE:
        utilidade += RU_SAFE * 0.7              # 7: protege parcialmente
    elif conflito.get("tipo") == "veiculo":
        utilidade += AV_PASS_SAFE * 0.6         # 6: desvio parcial
    elif conflito.get("tipo") == "obstaculo":
        utilidade += AV_PASS_SAFE * 0.75        # 7.5: desvio é ação certa
    utilidade += TRAFFIC_ENV_DAMAGE * 0.5       # -1: possível dano ambiental
    return utilidade


def calcular_utilidade_seguir(conflito):
    """Utilidade de SEGUIR. Ex2 do artigo: sinal verde → u_j = 9 (av_respects_rule)."""
    utilidade = 0.0
    if conflito.get("semaforo") == "aberto":
        utilidade += AV_RESPECTS_RULE           # 9: respeita regra de trânsito
    if conflito.get("tipo") in _TIPOS_PEDESTRE:
        utilidade -= RU_SAFE                    # -10: atropela pedestre
    elif conflito.get("tipo") == "veiculo":
        utilidade -= AV_PASS_SAFE * 0.5         # -5: risco de colisão frontal
    elif conflito.get("tipo") == "obstaculo":
        utilidade -= AV_PASS_SAFE               # -10: bate no obstáculo
    return utilidade


# ============================================================
# CENÁRIO DILEMA (Exemplo 1 do artigo):
# Pedestre + semaforo aberto + VEICULO ATRAS
# u_frear = ru_safe = 10  (protege pedestre)
# u_seguir = av_pass_safe = 10  (protege passageiro de colisão traseira)
# u_i = u_j = 10  →  Q1=Não → Q2=Não → HITL
# ============================================================

def calcular_utilidade_frear_dilema(conflito):
    """Frear com veiculo_atras: protege pedestre mas expõe passageiro."""
    # Pedestre na frente → frear = ru_safe (EG 2: protection of individuals)
    return float(RU_SAFE)   # 10


def calcular_utilidade_seguir_dilema(conflito):
    """Seguir com veiculo_atras: protege passageiro mas atropela pedestre."""
    # Veiculo atrás → seguir = av_pass_safe (EG 7: human life top priority)
    # Mas resulta também em atropelar pedestre → dilema genuíno (EG 8)
    return float(AV_PASS_SAFE)  # 10


def calcular_utilidade_desviar_dilema(conflito):
    """Desviar no dilema: não resolve completamente nenhum lado."""
    return RU_SAFE * 0.7 + TRAFFIC_ENV_DAMAGE * 0.5  # 7 - 1 = 6.0


def selecionar_melhor_acao_dilema(conflito):
    """Q1 para cenário dilema: u_frear = u_seguir = 10 → DILEMA."""
    u_frear   = calcular_utilidade_frear_dilema(conflito)
    u_desviar = calcular_utilidade_desviar_dilema(conflito)
    u_seguir  = calcular_utilidade_seguir_dilema(conflito)

    acoes = [("frear", u_frear), ("desviar", u_desviar), ("seguir", u_seguir)]
    acoes.sort(key=lambda x: x[1], reverse=True)

    melhor_acao, melhor_utilidade = acoes[0]
    segunda_utilidade = acoes[1][1]
    eh_dilema = abs(melhor_utilidade - segunda_utilidade) < 0.01

    return melhor_acao, melhor_utilidade, eh_dilema


def gerar_relatorio_dilema(conflito):
    """Relatório para cenário dilema."""
    u_frear   = calcular_utilidade_frear_dilema(conflito)
    u_desviar = calcular_utilidade_desviar_dilema(conflito)
    u_seguir  = calcular_utilidade_seguir_dilema(conflito)
    acao, utilidade, dilema = selecionar_melhor_acao_dilema(conflito)
    return HashableDict({
        "conflito": conflito,
        "utilidades": HashableDict({"frear": u_frear, "desviar": u_desviar, "seguir": u_seguir}),
        "acao_recomendada": acao,
        "utilidade_selecionada": utilidade,
        "eh_dilema": dilema,
    })


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def selecionar_melhor_acao(conflito):
    """Q1 (Fig. 2): existe utilidade maximizada? NB2: u1=u2 → dilema."""
    # Dilema usa funções próprias
    if conflito.get("tipo") == "pedestre_veiculo_atras":
        return selecionar_melhor_acao_dilema(conflito)

    u_frear = calcular_utilidade_frear(conflito)
    u_desviar = calcular_utilidade_desviar(conflito)
    u_seguir = calcular_utilidade_seguir(conflito)

    acoes = [("frear", u_frear), ("desviar", u_desviar), ("seguir", u_seguir)]
    acoes.sort(key=lambda x: x[1], reverse=True)

    melhor_acao, melhor_utilidade = acoes[0]
    segunda_utilidade = acoes[1][1]
    eh_dilema = abs(melhor_utilidade - segunda_utilidade) < 0.01

    return melhor_acao, melhor_utilidade, eh_dilema


def gerar_relatorio_utilidades(conflito):
    """Relatório completo para logging e HITL."""
    if conflito.get("tipo") == "pedestre_veiculo_atras":
        return gerar_relatorio_dilema(conflito)

    u_frear = calcular_utilidade_frear(conflito)
    u_desviar = calcular_utilidade_desviar(conflito)
    u_seguir = calcular_utilidade_seguir(conflito)
    acao, utilidade, dilema = selecionar_melhor_acao(conflito)
    return HashableDict({
        "conflito": conflito,
        "utilidades": HashableDict({"frear": u_frear, "desviar": u_desviar, "seguir": u_seguir}),
        "acao_recomendada": acao,
        "utilidade_selecionada": utilidade,
        "eh_dilema": dilema,
    })


# ============================================================
# FACTORY FUNCTIONS — Triângulo de Galtung (EUMAS 2024, Seção 3)
# Criam ConflitoGaltung a partir das percepções brutas do Ético.
# V3 é dinâmico: acao_va_padrao depende do semáforo.
# ============================================================

def criar_conflito_pedestre(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral):
    """Exemplo 2: pedestre sem carro atrás. V3: VA seguiria se sinal aberto."""
    acao_va_padrao = "seguir" if semaforo else "frear"
    return ConflitoGaltung(
        {"tipo": "pedestre", "semaforo": "aberto" if semaforo else "fechado", "posicao": "Cruzamento"},
        metas_incompativeis=("VA: respeitar_sinal_transito", "Etico: proteger_pedestre"),
        acoes_opostas=(acao_va_padrao, "frear"),
        crencas={"semaforo": semaforo, "pedestre": pedestre, "obstaculo": obstaculo,
                 "veiculo": veiculo, "veiculo_atras": v_atras, "veiculo_lateral": v_lateral},
    )


def criar_conflito_dilema(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral):
    """Exemplo 1: pedestre + veiculo atrás. Metas simétricas → DILEMA."""
    return ConflitoGaltung(
        {"tipo": "pedestre_veiculo_atras", "semaforo": "aberto" if semaforo else "fechado", "posicao": "Cruzamento"},
        metas_incompativeis=("VA: proteger_passageiro_colisao_traseira", "Etico: proteger_pedestre"),
        acoes_opostas=("seguir", "frear"),
        crencas={"semaforo": semaforo, "pedestre": pedestre, "obstaculo": obstaculo,
                 "veiculo": veiculo, "veiculo_atras": v_atras, "veiculo_lateral": v_lateral},
    )


def criar_conflito_obstaculo(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral):
    """Obstáculo simples ou Q4 (v_lateral).
    V3[1] (ação Ético) é dinâmico: semaforo=aberto → desviar (6.5 > 6); fechado → frear (7 > 6.5).
    Com v_lateral: desviar é enviado mas VA rejeita (Q3=Não) → Q4 redireciona para frear."""
    acao_va_padrao = "seguir" if semaforo else "frear"
    # semaforo=aberto: frear=6, desviar=6.5 → desviar vence
    # semaforo=fechado: frear=7, desviar=6.5 → frear vence (sem AV_DAMAGE)
    acao_etico = "desviar" if semaforo else "frear"
    if v_lateral:
        # V3[1]="desviar" (semaforo=aberto): VA rejeita via Q3 → Q4 → frear.
        # Galtung documenta a ação inicial recomendada, não a final após Q4.
        metas = ("VA: manter_trajetoria", "Etico: evitar_obstaculo_e_veiculo_lateral")
        acoes = (acao_va_padrao, acao_etico)
    else:
        metas = ("VA: manter_trajetoria", "Etico: evitar_obstaculo")
        acoes = (acao_va_padrao, acao_etico)
    return ConflitoGaltung(
        {"tipo": "obstaculo", "semaforo": "aberto" if semaforo else "fechado",
         "posicao": "Cruzamento", "veiculo_lateral": v_lateral},
        metas_incompativeis=metas,
        acoes_opostas=acoes,
        crencas={"semaforo": semaforo, "pedestre": pedestre, "obstaculo": obstaculo,
                 "veiculo": veiculo, "veiculo_atras": v_atras, "veiculo_lateral": v_lateral},
    )


def criar_conflito_veiculo(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral):
    """Veículo frontal. V3: VA manteria velocidade, Ético recomenda frear."""
    acao_va_padrao = "seguir" if semaforo else "frear"
    return ConflitoGaltung(
        {"tipo": "veiculo", "semaforo": "aberto" if semaforo else "fechado", "posicao": "Cruzamento"},
        metas_incompativeis=("VA: manter_velocidade", "Etico: evitar_colisao"),
        acoes_opostas=(acao_va_padrao, "frear"),
        crencas={"semaforo": semaforo, "pedestre": pedestre, "obstaculo": obstaculo,
                 "veiculo": veiculo, "veiculo_atras": v_atras, "veiculo_lateral": v_lateral},
    )


def criar_conflito_pedestre_zona_escolar(semaforo, pedestre, obstaculo, veiculo, v_atras, v_lateral):
    """Pedestre em zona escolar (zona_escolar=1).
    MODD threshold=4.0: semaforo=aberto → diff=3.0 < 4.0 → (transfer) → HITL.
                        semaforo=fechado → diff=4.0 >= 4.0 → (resolve) → VA executa."""
    acao_va_padrao = "seguir" if semaforo else "frear"
    return ConflitoGaltung(
        {"tipo": "pedestre_zona_escolar", "semaforo": "aberto" if semaforo else "fechado",
         "posicao": "Cruzamento", "zona_escolar": 1},
        metas_incompativeis=("VA: respeitar_sinal_transito", "Etico: proteger_pedestre_zona_escolar"),
        acoes_opostas=(acao_va_padrao, "frear"),
        crencas={"semaforo": semaforo, "pedestre": pedestre, "obstaculo": obstaculo,
                 "veiculo": veiculo, "veiculo_atras": v_atras, "veiculo_lateral": v_lateral,
                 "zona_escolar": 1},
    )
