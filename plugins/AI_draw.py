# -*- coding: utf-8 -*-
"""
@author: ForeverHaibara  https://github.com/ForeverHaibara
Credits to https://github.com/PaddlePaddle/PaddleHub
"""
from utils.utils import Listen, send
from mirai import Image
import aiohttp
import time 
import asyncio


@Listen.all_mesg()
async def AI_draw_ernievilg(event):
    """
    指令: /AI画画 + 风格 + 内容
    如: /AI画画 卡通 二次元美少女, 细腻, 温柔
    """
    if str(event.message_chain)=='/AI画画' or str(event.message_chain)=='/AI绘画':
        class ErnieVilG:
            def __init__(self, ak=None, sk=None):
                """
                :param ak: ak for applying token to request wenxin api.
                :param sk: sk for applying token to request wenxin api.
                """
                self.ak = ak or 'G26BfAOLpGIRBN5XrOV2eyPA25CE01lE'
                self.sk = sk or 'txLZOWIjEqXYMU3lSm05ViW4p9DWGOWs'
                self.token_host = 'https://wenxin.baidu.com/younger/portal/api/oauth/token'
                self.token = self._apply_token(self.ak, self.sk)

            async def _apply_token(self, ak, sk):
                ak = ak or self.ak
                sk = sk or self.sk
                
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),timeout=timeout) as session:
                    async with session.get(url=self.token_host,
                                            params={'grant_type': 'client_credentials',
                                                    'client_id': ak,
                                                    'client_secret': sk
                                                    }
                                            ) as resp:
                        res = await resp.json()  
                        
                return res['data']

            async def generate_image(self,
                            text_prompt: str,
                            style: str = "油画") -> list:
                token = self.token
                create_url = 'https://wenxin.baidu.com/younger/portal/api/rest/1.0/ernievilg/v1/txt2img?from=paddlehub'
                get_url = 'https://wenxin.baidu.com/younger/portal/api/rest/1.0/ernievilg/v1/getImg?from=paddlehub'
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                taskids = []
                assert style in ('油画','水彩','粉笔画','卡通','儿童画','蜡笔画','探索无限'),\
                                '风格暂时只支持 油画、水彩、粉笔画、卡通、儿童画、蜡笔画、探索无限 中的一种'

                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),timeout=timeout) as session:
                    async with session.post(url=create_url,
                                        json={'access_token': token, "text": text_prompt, "style": style},
                                        headers=headers) as resp:
                        res = await resp.json()
                        
                if res['code'] == 100 or res['code'] == 110 or res['code'] == 111:
                    token = self._apply_token(self.ak, self.sk)                    
                    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),timeout=timeout) as session:
                        async with session.post(url=create_url,
                                            json={'access_token': token, "text": text_prompt, "style": style},
                                            headers=headers) as resp:
                            res = await resp.json()
                            
                if res['msg'] == 'success':
                    taskids.append(res['data']["taskId"])
                else:
                    print(res['msg'])
                    # raise RuntimeError(res['msg'])

                results = {}
                start_time = time.time()
                while len(taskids): # retries 
                    if time.time() - start_time > 300:
                        return [] 
                    
                    has_done = []
                    for taskid in taskids:           
                        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),timeout=timeout) as session:
                            async with session.post(url=get_url,
                                                json={'access_token': token, 'taskId': {taskid}},
                                                headers=headers) as resp:
                                res = await resp.json()
                                
                        if res['code'] == 100 or res['code'] == 110 or res['code'] == 111:
                            token = self._apply_token(self.ak, self.sk)
                            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False),timeout=timeout) as session:
                                async with session.post(url=get_url,
                                                    json={'access_token': token, 'taskId': {taskid}},
                                                    headers=headers) as resp:
                                    res = await resp.json()
                                    
                        if res['msg'] == 'success':
                            if res['data']['status'] == 1:
                                has_done.append(res['data']['taskId'])
                            results[res['data']['text']] = {'imgUrls': res['data']['imgUrls']}
                        else:
                            print(res['msg'])
                            # raise RuntimeError(res['msg'])
                            
                    # do not post requests too frequently, because it takes time to generate images at server
                    
                    await asyncio.sleep(3) 
                    for taskid in has_done:
                        taskids.remove(taskid)
                    

                urls = [image['image'] for image in list(results.values())[0]['imgUrls']]
                return urls 


        splits = str(event.message_chain).split()
        if len(splits) >= 3:
            style = splits[1]
            texts = ' '.join(splits[2:])

        if len(splits) <= 2:
            await send(event, '参数错误, 应为 /AI画画 + 风格 + 内容')
            return 

        if style not in ('油画','水彩','粉笔画','卡通','儿童画','蜡笔画','探索无限'):
            await send(event, '风格只支持 油画、水彩、粉笔画、卡通、儿童画、蜡笔画、探索无限 哦')
            return 

        # 6 image urls in the list
        urls = ErnieVilG().generate_image(text_prompt = texts, style = style)

        await send(event, ['风格:%s\n内容:%s'%(style, texts)] + [Image(url=url) for url in urls])   
