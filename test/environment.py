from maspy import *
from utilities import HashableDict


class AmbienteUrbano(Environment):

    def __init__(self, env_name):
        super().__init__(env_name)
        self.create(Percept("semaforo_aberto",    1))  # sinal verde
        self.create(Percept("pedestre_detectado", 1))  # pedestre presente
        self.create(Percept("obstaculo",          0))  # sem obstáculo
        self.create(Percept("veiculo_detectado",  0))  # sem veículo frontal
        self.create(Percept("veiculo_atras",      0))  # sem carro atrás
        self.create(Percept("veiculo_lateral",    0))  # sem veículo lateral
        # zona_escolar=1 → ativa cenário MODD (transfer): diff=3.0 < threshold=4.0
        self.create(Percept("zona_escolar",       0))  # sem zona escolar

    def executar_movimento(self, src, movimento):
        """Atuador: VA executa movimento no ambiente."""
        self.print(f"Movimento executado por {src}: {movimento}")
        if movimento in ["frear", "desviar"]:
            self.print(f"Conflito resolvido com acao: {movimento}")
            self.create(Percept("conflito_resolvido", HashableDict({
                "acao": movimento, "agente": str(src)
            })))

    def registrar_evento(self, src, evento):
        self.print(f"Evento registrado por {src}: {evento}")
        self.create(Percept("evento_registrado", evento))
