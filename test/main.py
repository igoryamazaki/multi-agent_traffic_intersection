# ============================================================
# main.py - Inicialização do SMA (Sistema Multi-Agente)
#
# Selecione o cenário alterando a variável CENARIO:
#
#   "exemplo2"  -> Exemplo 2 do artigo
#                  Pedestre + sinal verde, sem carro atrás
#                  u_frear=10, u_seguir=9 -> Q1=Sim -> frear
#                  VA: Q3=Sim -> aceita -> executa
#
#   "dilema"    -> Exemplo 1 do artigo
#                  Pedestre + sinal verde + carro atrás
#                  u_frear=10, u_seguir=10 -> Q1=Nao -> HITL
#                  VA: aguarda handover (EG 19)
#
#   "q4"        -> Cenario Q4
#                  Obstaculo + veiculo lateral
#                  Etico recomenda desviar (obstaculo); VA percebe
#                  veiculo_lateral -> Q3=Nao -> Q4=Sim -> pede detalhes
# ============================================================

from maspy import *
from environment import AmbienteUrbano
from agent_va import AgenteVA
from agent_ethical import AgenteEtico
from agent_hitl import AgenteHITL

def main():
    print("=" * 60)
    print("  Arquitetura Etica para Veiculos Autonomos")
    print("=" * 60)

    # Passo 1: Ambiente urbano (cruzamento)
    # Para mudar o cenario, edite os Percepts em environment.py
    cruzamento = AmbienteUrbano("Cruzamento")
    print("[Setup] Ambiente 'Cruzamento' criado")

    # Passo 2: Agentes
    agente_va = AgenteVA("VA")
    agente_etico = AgenteEtico("AgenteEtico")
    agente_hitl = AgenteHITL("HITL")
    print("[Setup] Agentes: VA, AgenteEtico, HITL")

    # Passo 3: Canal de comunicação (ECP via Contract Net)
    canal = Channel("AgentComm")
    print("[Setup] Canal 'AgentComm' criado")

    # Passo 4: Conectar tudo
    Admin().connect_to(
        [agente_va, agente_etico, agente_hitl],
        [canal, cruzamento]
    )
    print("[Setup] Agentes conectados ao ambiente e canal")

    # Passo 5: Relatorio
    Admin().report = True

    # Passo 6: Iniciar
    print("\n" + "=" * 60)
    print("  Iniciando SMA... Etico monitora -> ECP -> VA decide")
    print("=" * 60 + "\n")

    Admin().start_system()

    print("\n" + "=" * 60)
    print("  Execucao finalizada!")
    print("=" * 60)


if __name__ == "__main__":
    main()
