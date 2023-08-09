from io import BytesIO
import json
import pathlib
import alibabacloud_ocr_api20210707.client
import alibabacloud_tea_openapi.models
import alibabacloud_ocr_api20210707.models
import alibabacloud_tea_util.models


class AliyunOCR:
    def __init__(self, access_key_id, access_key_secret):
        config = alibabacloud_tea_openapi.models.Config(
            access_key_id=access_key_id, access_key_secret=access_key_secret
        )
        config.endpoint = "ocr-api.cn-hangzhou.aliyuncs.com"
        self.client = alibabacloud_ocr_api20210707.client.Client(config)

    def request(self, filename: bytes | str | pathlib.Path) -> str:
        if isinstance(filename, (str, pathlib.Path)):
            with open(filename, "rb") as f:
                file_content = f.read()
        elif isinstance(filename, bytes):
            file_content = filename
        else:
            raise TypeError(f"Unknown type {type(filename)} for filename")

        body = BytesIO()
        body.write(file_content)
        body.seek(0)

        recognize_general_request = (
            alibabacloud_ocr_api20210707.models.RecognizeGeneralRequest(body=body)
        )
        runtime = alibabacloud_tea_util.models.RuntimeOptions()
        resp = self.client.recognize_general_with_options(
            recognize_general_request, runtime
        )
        return json.loads(resp.body.data)["content"]
