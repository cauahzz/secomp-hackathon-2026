from atlas_vision.models import ROI
from atlas_vision.roi import assign_detections_to_rois, feet_point, scale_roi


def test_escala_e_ponto_dos_pes():
    roi = ROI("ROI-01", "room-101", "Sala", {"x": 10, "y": 20, "width": 100, "height": 50})
    scaled = scale_roi(roi, 2560, 1440, 1280, 720)
    assert (scaled.x, scaled.y, scaled.width, scaled.height) == (20, 40, 200, 100)
    assert feet_point((0, 0, 10, 20)) == (5, 20)


def test_pertencimento_usa_os_pes_e_uma_roi_so():
    a = ROI("A", "s1", "A", {"x": 0, "y": 0, "width": 100, "height": 100})
    b = ROI("B", "s2", "B", {"x": 100, "y": 0, "width": 100, "height": 100})
    rois = [scale_roi(a, 200, 100, 200, 100), scale_roi(b, 200, 100, 200, 100)]
    # A terceira caixa tem o centro em A e os pés na fronteira: conta para B.
    counts = assign_detections_to_rois([(10, 0, 20, 90), (110, 0, 120, 90), (95, 0, 105, 90)], rois)
    assert counts == {"A": 1, "B": 2}


def test_pessoa_fora_de_qualquer_roi_nao_conta():
    a = ROI("A", "s1", "A", {"x": 0, "y": 0, "width": 50, "height": 50})
    rois = [scale_roi(a, 100, 100, 100, 100)]
    assert assign_detections_to_rois([(60, 0, 70, 90)], rois) == {"A": 0}


def test_todas_as_rois_aparecem_mesmo_vazias():
    a = ROI("A", "s1", "A", {"x": 0, "y": 0, "width": 50, "height": 50})
    b = ROI("B", "s2", "B", {"x": 50, "y": 0, "width": 50, "height": 50})
    rois = [scale_roi(a, 100, 50, 100, 50), scale_roi(b, 100, 50, 100, 50)]
    assert assign_detections_to_rois([], rois) == {"A": 0, "B": 0}
