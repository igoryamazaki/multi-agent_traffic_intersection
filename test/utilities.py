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

def calcular_utilidade_frear(conflito):
    """Utilidade de FREAR. Ex2 do artigo: pedestre → u_i = 10 (ru_safe)."""
    utilidade = 0.0
    if conflito.get("tipo") == "pedestre":
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
    if conflito.get("tipo") == "pedestre":
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
    if conflito.get("tipo") == "pedestre":
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
