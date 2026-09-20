from pathlib import Path

import pytest

from evaluate import frame_keys, load_manual


def write_csv(tmp_path, text, encoding="utf-8"):
    path = tmp_path / "manual.csv"
    path.write_text(text, encoding=encoding)
    return str(path)


def test_le_anotacao_manual(tmp_path):
    csv_path = write_csv(
        tmp_path,
        "frame,region_id,manual_count\nframe_000.jpg,ROI-01,4\nframe_000.jpg,ROI-02,2\n",
    )
    assert load_manual(csv_path) == {
        ("frame_000.jpg", "ROI-01"): 4,
        ("frame_000.jpg", "ROI-02"): 2,
    }


def test_ignora_espacos_e_bom_da_planilha(tmp_path):
    csv_path = write_csv(
        tmp_path,
        "frame,region_id,manual_count\n frame_000.jpg , ROI-01 , 4 \n",
        encoding="utf-8-sig",
    )
    assert load_manual(csv_path) == {("frame_000.jpg", "ROI-01"): 4}


def test_coluna_faltando_avisa_qual(tmp_path):
    csv_path = write_csv(tmp_path, "frame,manual_count\nframe_000.jpg,4\n")
    with pytest.raises(SystemExit, match="region_id"):
        load_manual(csv_path)


def test_contagem_invalida_aponta_a_linha(tmp_path):
    csv_path = write_csv(
        tmp_path, "frame,region_id,manual_count\nframe_000.jpg,ROI-01,quatro\n"
    )
    with pytest.raises(SystemExit, match=":2:"):
        load_manual(csv_path)


def test_nomes_aceitos_para_o_mesmo_frame():
    """A equipe anota à mão: 0 e 000 valem tanto quanto frame_000.jpg."""
    assert frame_keys(Path("data/eval_frames/frame_000.jpg")) == [
        "frame_000.jpg",
        "frame_000",
        "000",
        "0",
    ]


def test_nome_sem_indice_numerico():
    assert frame_keys(Path("recorte.jpg")) == ["recorte.jpg", "recorte", "recorte"]
