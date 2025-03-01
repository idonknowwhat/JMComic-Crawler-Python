from .jm_toolkit import *

"""

Response Entity

"""


class JmResp(CommonResp):

    @property
    def is_success(self) -> bool:
        return self.http_code == 200 and len(self.content) != 0


class JmImageResp(JmResp):

    def require_success(self):
        if self.is_success:
            return

        msg = f'禁漫图片获取失败: [{self.url}]'
        if self.http_code != 200:
            msg += f'，http状态码={self.http_code}'
        if len(self.content) == 0:
            msg += f'，响应数据为空'

        raise AssertionError(msg)

    def transfer_to(self,
                    path,
                    scramble_id,
                    decode_image=True,
                    img_url=None,
                    ):
        img_url = img_url or self.url

        if decode_image is False:
            # 不解密图片，直接返回
            JmImageSupport.save_resp_img(
                self,
                path,
                need_convert=suffix_not_equal(img_url, path),
            )
        else:
            # 解密图片，需要 photo_id、scramble_id
            JmImageSupport.decode_and_save(
                JmImageSupport.get_num_by_url(scramble_id, img_url),
                JmImageSupport.open_Image(self.content),
                path,
            )


class JmApiResp(JmResp):

    @classmethod
    def wrap(cls, resp, key_ts):
        if isinstance(resp, JmApiResp):
            raise AssertionError('重复包装')

        return cls(resp, key_ts)

    def __init__(self, resp, key_ts):
        super().__init__(resp)
        self.key_ts = key_ts
        self.cache_decode_data = None

    @staticmethod
    def parseData(text, time):
        import hashlib
        import base64
        from Crypto.Cipher import AES
        # key为时间+18comicAPPContent的md5结果
        key = hashlib.md5(f"{time}18comicAPPContent".encode()).hexdigest().encode()
        cipher = AES.new(key, AES.MODE_ECB)
        # 先将数据进行base64解码
        data = base64.b64decode(text)
        # 再进行AES-ECB解密
        paddedPlainText = cipher.decrypt(data)
        # 将得到的数据进行Utf8解码
        res = paddedPlainText.decode('utf-8')
        # 得到的数据再末尾有一些乱码
        i = len(res) - 1
        while i >= 0 and res[i] == '\x0c':
            i -= 1
        return res[:i + 1]

    @property
    def decoded_data(self) -> str:
        if self.cache_decode_data is None:
            self.cache_decode_data = self.parseData(self.encoded_data, self.key_ts)

        return self.cache_decode_data

    @property
    def encoded_data(self) -> str:
        return self.json()['data']

    @property
    def res_data(self) -> Any:
        self.require_success()
        from json import loads
        return loads(self.decoded_data)

    def json(self, **kwargs) -> Dict:
        return self.resp.json()

    def model(self) -> DictModel:
        return DictModel(self.json())

    @property
    def model_data(self) -> DictModel:
        self.require_success()
        return DictModel(self.res_data)


"""

Client Interface

"""


class JmDetailClient:

    def get_album_detail(self, album_id) -> JmAlbumDetail:
        raise NotImplementedError

    def get_photo_detail(self, photo_id: str, album=True) -> JmPhotoDetail:
        raise NotImplementedError

    def ensure_photo_can_use(self, photo_detail: JmPhotoDetail):
        raise NotImplementedError

    def search_album(self, search_query, main_tag=0) -> Union[JmSearchPage, JmAlbumDetail]:
        raise NotImplementedError

    def of_api_url(self, api_path, domain):
        raise NotImplementedError

    def enable_cache(self, debug=False):
        raise NotImplementedError


class JmUserClient:

    def login(self,
              username,
              password,
              refresh_client_cookies=True,
              id_remember='on',
              login_remember='on',
              ):
        raise NotImplementedError


class JmImageClient:

    # -- 下载图片 --

    def download_image(self,
                       img_url: str,
                       img_save_path: str,
                       scramble_id: str,
                       decode_image=True,
                       ):
        """
        下载JM的图片
        @param img_url: 图片url
        @param img_save_path: 图片保存位置
        @param scramble_id: 图片所在photo的scramble_id
        @param decode_image: 要保存的是解密后的图还是原图
        """
        # 请求图片
        resp = self.get_jm_image(img_url)

        resp.require_success()

        # gif图无需加解密，需要最先判断

        if self.img_is_not_need_to_decode(img_url, resp):
            JmImageSupport.save_resp_img(resp, img_save_path, False)
        else:
            resp.transfer_to(img_save_path, scramble_id, decode_image, img_url)

    def download_by_image_detail(self,
                                 img_detail: JmImageDetail,
                                 img_save_path,
                                 decode_image=True,
                                 ):
        self.download_image(
            img_detail.img_url,
            img_save_path,
            img_detail.scramble_id,
            decode_image=decode_image,
        )

    def get_jm_image(self, img_url) -> JmImageResp:
        raise NotImplementedError

    @classmethod
    def img_is_not_need_to_decode(cls, data_original: str, _resp):
        return data_original.endswith('.gif')


class JmcomicClient(
    JmImageClient,
    JmDetailClient,
    JmUserClient,
):
    pass
