import json
import alibabacloud_ocr_api20210707.client
import alibabacloud_tea_openapi.models
import alibabacloud_darabonba_stream.client
import alibabacloud_ocr_api20210707.models
import alibabacloud_tea_util.models


class AliyunOCR:
    def __init__(self, access_key_id, access_key_secret):
        config = alibabacloud_tea_openapi.models.Config(
            access_key_id=access_key_id, access_key_secret=access_key_secret
        )
        config.endpoint = "ocr-api.cn-hangzhou.aliyuncs.com"
        self.client = alibabacloud_ocr_api20210707.client.Client(config)

    def request(self, filename) -> str:
        body = alibabacloud_darabonba_stream.client.Client.read_from_file_path(filename)
        recognize_general_request = (
            alibabacloud_ocr_api20210707.models.RecognizeGeneralRequest(body=body)
        )
        runtime = alibabacloud_tea_util.models.RuntimeOptions()
        resp = self.client.recognize_general_with_options(
            recognize_general_request, runtime
        )
        return json.loads(resp.body.data)["content"]
