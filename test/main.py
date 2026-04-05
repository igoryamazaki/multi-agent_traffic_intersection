# ============================================================
# main.py - Inicialização do SMA (Sistema Multi-Agente)
#
# ============================================================

from maspy import *
from environment import AmbienteUrbano
from agent_va import AgenteVA
from agent_ethical import AgenteEtico
from agent_hitl import AgenteHITL


def main():
    print("=" * 60)
    print("  ADFERS - SMA com Agentes BDI em MASPY")
    print("  Arquitetura Ética para Veículos Autônomos")
    print("=" * 60)

    # Passo 1: Ambiente urbano (cruzamento)
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

    # Passo 5: Relatório
    Admin().report = True

    # Passo 6: Iniciar
    print("\n" + "=" * 60)
    print("  Iniciando SMA... Etico monitora -> ECP -> VA decide")
    print("=" * 60 + "\n")

    Admin().start_system()

    print("\n" + "=" * 60)
    print("  Execução finalizada!")
    print("=" * 60)


if __name__ == "__main__":
    main()
