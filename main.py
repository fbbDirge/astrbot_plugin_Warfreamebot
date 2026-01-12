import asyncio
import traceback
import json
from astrbot.api.all import *
from astrbot.api.event import filter

# 尝试导入 curl_cffi，这是目前过 CF 最强的库
try:
    from curl_cffi.requests import AsyncSession
except ImportError:
    raise ImportError("缺少关键依赖，请执行: pip install curl_cffi")

@register("astrbot_plugin_warframe", "YourName", "Warframe助手", "1.7.0", "TLS指纹伪装版")
class WarframePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://api.warframestat.us/pc?language=zh"

    # --- 核心：使用 curl_cffi 获取数据 ---
    async def fetch_worldstate(self):
        try:
            # impersonate="chrome120": 关键参数！模拟 Chrome 120 的 TLS 指纹
            # 这样 Cloudflare 看到的就像是一个真实的浏览器发起的加密连接
            async with AsyncSession(impersonate="chrome120") as session:
                print(f"[WF] 正在通过 TLS 伪装请求: {self.api_url}")
                
                response = await session.get(
                    self.api_url, 
                    timeout=20
                )
                
                if response.status_code == 200:
                    return json.loads(response.text) # curl_cffi 返回的是 text
                elif response.status_code == 403:
                    return f"403被拦截 (即使伪装也被挡，IP信誉过低)"
                else:
                    return f"API请求失败: {response.status_code}"

        except Exception as e:
            return f"请求异常: {str(e)}"

    # --- 指令 1: 平原 ---
    @filter.command("平原") 
    async def check_all_plains(self, event: AstrMessageEvent):
        '''查询所有平原时间'''
        try:
            yield event.plain_result("📡 正在连接虚空 (TLS指纹模式)...")
            
            data = await self.fetch_worldstate()
            
            if isinstance(data, str):
                yield event.plain_result(f"❌ {data}")
                return
            
            msg = "🌌 各平原时间状态：\n"

            # 1. 夜灵平原
            cetus = data.get('cetusCycle', {})
            if cetus:
                state = "☀️白天" if cetus.get('isDay') else "🌙夜晚"
                left = cetus.get('timeLeft', '?')
                msg += f"【夜灵平原】: {state}\n- 剩余: {left}\n"
            
            # 2. 福尔图娜
            vallis = data.get('vallisCycle', {})
            if vallis:
                state = "🔥温暖" if vallis.get('isWarm') else "❄️寒冷"
                left = vallis.get('timeLeft', '?')
                msg += f"【福尔图娜】: {state}\n- 剩余: {left}\n"

            # 3. 魔胎之境
            cambion = data.get('cambionCycle', {})
            if cambion:
                active = cambion.get('active', 'unknown')
                state_name = "🔴Fass" if active == 'fass' else "🔵Vome" if active == 'vome' else active
                left = cambion.get('timeLeft', '?')
                msg += f"【魔胎之境】: {state_name}\n- 剩余: {left}\n"

            # 4. 双衍王境
            duviri = data.get('duviriCycle', {})
            if duviri:
                msg += f"【双衍王境】: {duviri.get('state', '未知').capitalize()}\n- 剩余: {duviri.get('timeLeft', '?')}\n"

            # 5. 地球
            earth = data.get('earthCycle', {})
            if earth:
                state = "☀️白天" if earth.get('isDay') else "🌙夜晚"
                msg += f"【地球】: {state}\n- 剩余: {earth.get('timeLeft', '?')}"

            yield event.plain_result(msg)

        except Exception as e:
            traceback.print_exc()
            yield event.plain_result(f"❌ 插件错误: {str(e)}")

    # --- 指令 2: 突击 ---
    @filter.command("突击")
    async def check_sortie(self, event: AstrMessageEvent):
        '''查询今日突击信息'''
        try:
            data = await self.fetch_worldstate()
            
            if isinstance(data, str):
                yield event.plain_result(f"❌ {data}")
                return

            sortie = data.get('sortie', {})
            if not sortie or sortie.get('expired'):
                yield event.plain_result("⚠️ 当前无突击任务")
                return

            msg = f"⚔️ 今日突击: {sortie.get('boss')} ({sortie.get('faction')})\n"
            
            if 'variants' in sortie:
                cn_nums = ['一', '二', '三']
                for i, v in enumerate(sortie['variants']):
                    num = cn_nums[i] if i < 3 else str(i+1)
                    msg += f"----------------\n[{num}] {v.get('missionType')}\n📍 {v.get('node')}\n⚠️ {v.get('modifier')}\n"
            
            msg += f"----------------\n⏳ 剩余: {sortie.get('eta')}"
            yield event.plain_result(msg)

        except Exception as e:
            yield event.plain_result(f"❌ 插件错误: {str(e)}")