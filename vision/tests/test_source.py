from atlas_vision.source import OpenCVSource, frame_sampling_step, is_live_source


def test_arquivo_nao_e_live():
    assert is_live_source("data/demo.mp4", "file") is False


def test_arquivo_servido_por_http_continua_arquivo():
    """Precisa voltar ao início no fim, senão a demo vira no_data em 30 s."""
    assert is_live_source("http://host/demo.mp4", "file") is False


def test_stream_e_live():
    assert is_live_source("rtsp://host/stream", "file") is True
    assert is_live_source("http://host/stream", "stream") is True


def test_webcam_e_live():
    assert is_live_source(0, "file") is True
    assert is_live_source("qualquer", "webcam") is True


def test_http_sem_tipo_declarado_assume_stream():
    assert is_live_source("http://host/stream", "") is True


def test_passo_de_amostragem():
    assert frame_sampling_step(30.0, 3.0) == 10
    assert frame_sampling_step(25.0, 3.0) == 8
    # Nunca menos de um frame, mesmo pedindo mais fps do que o vídeo tem.
    assert frame_sampling_step(2.0, 5.0) == 1
    assert frame_sampling_step(0.0, 3.0) == 1


class FakeCap:
    """Conta grab() para testar o descarte de frames sem decodificação."""

    def __init__(self, available):
        self.available = available
        self.grabs = 0

    def grab(self):
        if self.grabs >= self.available:
            return False
        self.grabs += 1
        return True


def make_source(cap):
    source = OpenCVSource.__new__(OpenCVSource)
    source.cap = cap
    return source


def test_skip_descarta_o_pedido():
    source = make_source(FakeCap(10))
    assert source.skip(3) == 3
    assert source.cap.grabs == 3


def test_skip_para_no_fim_do_video():
    source = make_source(FakeCap(2))
    assert source.skip(5) == 2


def test_skip_sem_fonte_aberta():
    assert make_source(None).skip(3) == 0


def test_skip_ignora_pedido_nao_positivo():
    source = make_source(FakeCap(10))
    assert source.skip(0) == 0
    assert source.skip(-1) == 0
    assert source.cap.grabs == 0
