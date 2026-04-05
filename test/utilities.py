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


RU_SAFE = 10              # Usuários da via seguros (EG 1, 2)
AV_PASS_SAFE = 10         # Passageiros do VA seguros (EG 7)
AV_RESPECTS_RULE = 9      # VA respeitou regras de trânsito (EG 5)
AV_DAMAGE = -1             # Dano menor ao VA
TRAFFIC_ENV_DAMAGE = -2    # Dano ao ambiente de trânsito


def calcular_utilidade_frear(conflito):
    """Utilidade de FREAR. Ex2 do artigo: pedestre → u_i = 10."""
    utilidade = 0.0
    if conflito.get("tipo") == "pedestre":
        utilidade += RU_SAFE
    elif conflito.get("tipo") == "veiculo":
        utilidade += AV_PASS_SAFE * 0.8
    elif conflito.get("tipo") == "obstaculo":
        utilidade += AV_PASS_SAFE * 0.7
    if conflito.get("semaforo") == "aberto":
        utilidade += AV_DAMAGE
    return utilidade


def calcular_utilidade_desviar(conflito):
    """Utilidade de DESVIAR. Protege parcialmente com risco ambiental."""
    utilidade = 0.0
    if conflito.get("tipo") == "pedestre":
        utilidade += RU_SAFE * 0.7
    elif conflito.get("tipo") == "veiculo":
        utilidade += AV_PASS_SAFE * 0.6
    utilidade += TRAFFIC_ENV_DAMAGE * 0.5
    return utilidade


def calcular_utilidade_seguir(conflito):
    """Utilidade de SEGUIR. Ex2 do artigo: sinal verde → u_j = 9."""
    utilidade = 0.0
    if conflito.get("semaforo") == "aberto":
        utilidade += AV_RESPECTS_RULE
    if conflito.get("tipo") == "pedestre":
        utilidade -= RU_SAFE
    elif conflito.get("tipo") == "veiculo":
        utilidade -= AV_PASS_SAFE * 0.5
    return utilidade


def selecionar_melhor_acao(conflito):
    """Q1 (Fig. 2): existe utilidade maximizada? NB2: u1=u2 → dilema."""
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
