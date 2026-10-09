import json
from pathlib import Path
import pytest
from ledger_htr.data import read_jsonl, write_jsonl, resolve_crop, sha256
from ledger_htr.imports import import_transkribus


def test_duplicate_reference_ids_are_rejected(tmp_path):
    path = tmp_path / "references.jsonl"
    write_jsonl(path, [{"id": "one"}, {"id": "one"}])
    with pytest.raises(ValueError, match="Duplicate"):
        read_jsonl(path)


def test_crop_integrity_and_path_escape(tmp_path):
    image = tmp_path / "crop.png"
    image.write_bytes(b"fixture bytes")
    assert resolve_crop(tmp_path, {"id": "one", "image": "crop.png", "image_sha256": sha256(image)}) == image
    with pytest.raises(ValueError, match="checksum"):
        resolve_crop(tmp_path, {"id": "one", "image": "crop.png", "image_sha256": "wrong"})
    with pytest.raises(ValueError, match="escapes"):
        resolve_crop(tmp_path, {"id": "one", "image": "../outside.png"})


def test_transkribus_import_preserves_literal_amount_and_source_identity(tmp_path):
    path = tmp_path / "crop-1.txt"
    path.write_text(' 300 "\n')
    result = import_transkribus(tmp_path, [{"id": "crop-1", "image_sha256": "fixture-hash"}], "fixture-model")
    assert result[0]["text"] == '300 "'
    assert result[0]["image_sha256"] == "fixture-hash"
    assert result[0]["export_sha256"] == sha256(path)
    assert result[0]["provider"] == "Transkribus"


def test_transkribus_import_rejects_unmapped_exports(tmp_path):
    (tmp_path / "unmapped.txt").write_text("Cash")
    with pytest.raises(ValueError, match="Unknown crop"):
        import_transkribus(tmp_path, [], "fixture-model")


def test_model_tampering_is_rejected(tmp_path):
    from ledger_htr.provenance import record_model, verify_model
    (tmp_path / 'data').mkdir()
    model = tmp_path / 'model'; model.mkdir()
    (model / 'config.json').write_text('{}')
    record_model(tmp_path, model)
    verify_model(tmp_path, model)
    (model / 'config.json').write_text('{"changed":true}')
    with pytest.raises(ValueError, match='checksum'):
        verify_model(tmp_path, model)


def test_page_export_preserves_order_and_drops_account_metadata(tmp_path):
    from zipfile import ZipFile
    from ledger_htr.page_export import read_page_export
    path = tmp_path / 'fixture.zip'
    xml = '''<PcGts xmlns="urn:page"><Metadata><Creator>version=2.51.0:model_id=53042:lm=none</Creator><Private>account@example.com</Private></Metadata><Page imageWidth="100" imageHeight="200"><ReadingOrder><OrderedGroup><RegionRefIndexed index="0" regionRef="r"/></OrderedGroup></ReadingOrder><TextRegion id="r"><TextLine id="b" custom="readingOrder {index:1;}"><Coords points="1,2 3,4"/><TextEquiv><Unicode>300 "</Unicode></TextEquiv></TextLine><TextLine id="a" custom="readingOrder {index:0;}"><Coords points="1,2 3,4"/><TextEquiv><Unicode>Cash</Unicode></TextEquiv></TextLine></TextRegion></Page></PcGts>'''
    with ZipFile(path, 'w') as z: z.writestr('doc/page/one.xml', xml)
    result = read_page_export(path, 'source-hash', 'fixture-model')
    assert [x['text'] for x in result['regions'][0]['lines']] == ['Cash', '300 "']
    assert result['model_id'] == '53042'
    assert 'account@example.com' not in json.dumps(result)
