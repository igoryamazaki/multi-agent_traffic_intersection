# ============================================================
# environment.py - Ambiente Urbano de Trânsito (Ute)
#
# Conforme Fig. 1 (EAA): tanto o AV-agent quanto o Ethical
# Agent percebem o ambiente via sensores. O AV-agent age
# no ambiente via atuadores (hit the brakes, turn left...).
# ============================================================

from maspy import *
from utilities import HashableDict


class AmbienteUrbano(Environment):

    def __init__(self, env_name):
        super().__init__(env_name)
        # Cenário: semáforo verde + pedestre atravessando
        self.create(Percept("semaforo_aberto", 1))
        self.create(Percept("pedestre_detectado", 0))
        self.create(Percept("obstaculo", 1))
        self.create(Percept("veiculo_detectado", 0))

    def executar_movimento(self, src, movimento):
        """Atuador: VA executa movimento no ambiente."""
        self.print(f"Movimento executado por {src}: {movimento}")
        if movimento in ["frear", "desviar"]:
            self.print(f"Conflito resolvido com ação: {movimento}")
            self.create(Percept("conflito_resolvido", HashableDict({
                "acao": movimento, "agente": str(src)
            })))

    def registrar_evento(self, src, evento):
        self.print(f"Evento registrado por {src}: {evento}")
        self.create(Percept("evento_registrado", evento))
