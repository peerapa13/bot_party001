import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from MSV import server_on
import feedparser
import asyncio
from datetime import datetime, time
import pytz
import logging
import re
import random

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

tz = pytz.timezone('Asia/Bangkok')

# 1. กำหนดเวลาส่งข่าว
times = [
    time(hour=6, minute=30),
    time(hour=16, minute=30)
]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="/", intents=intents)

CHANNEL_New = int(os.getenv("CHANNEL_New", 0))
CHANNEL_W = int(os.getenv("CHANNEL_W", 0))

NEWS_SOURCES = [
    {"url": "https://www.thairath.co.th/rss/news", "name": "Thairath"},
    {"url": "https://www.techtalkthai.com/feed/", "name": "TechTalkThai"},
    {"url": "https://www.matichon.co.th/feed", "name": "มติชน"},
    {"url": "https://www.bbc.com/thai/index.xml", "name": "BBC Thai"},
]

sent_articles = set()

async def fetch_news(max_articles=5):
    all_articles = []
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source['url'])
            count = 0
            for entry in feed.entries:
                if count >= 2: break
                image_url = None
                if 'media_content' in entry:
                    image_url = entry.media_content[0]['url']
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            image_url = link.href
                
                article = {
                    'title': entry.get('title', 'ไม่มีหัวข้อ'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', 'ไม่มีรายละเอียด'),
                    'source': source['name'],
                    'image': image_url
                }
                
                if article['link'] and article['link'] not in sent_articles:
                    all_articles.append(article)
                    count += 1
        except Exception as e:
            logger.error(f"❌ Error fetching from {source['name']}: {e}")
            
    random.shuffle(all_articles)
    return all_articles[:max_articles]

async def send_news_to_discord(articles):
    channel = bot.get_channel(CHANNEL_New)
    if not channel or not articles:
        return False

    embeds = []
    for article in articles:
        # ลบ HTML Tags ออกจาก Summary
        clean_summary = re.sub(r'<[^>]+>', '', article['summary'])
        if len(clean_summary) > 300:
            clean_summary = clean_summary[:297] + "..."

        embed = discord.Embed(
            title=article['title'][:250],
            url=article['link'],
            description=clean_summary,
            color=0x2b2d31, # สีเทาเข้มแบบ Discord สวยงาม
            timestamp=datetime.now(tz)
        )
        embed.set_footer(text=f"ที่มา: {article['source']}")
        if article['image']:
            embed.set_image(url=article['image'])
        
        embeds.append(embed)
        sent_articles.add(article['link'])

    # ส่งทีละ 5 embeds เพื่อความสวยงามและไม่ยาวเกินไป
    for i in range(0, len(embeds), 5):
        batch = embeds[i:i+5]
        header = f"📰 **สรุปข่าวรอบเวลา {datetime.now(tz).strftime('%H:%M')} น.**" if i == 0 else ""
        await channel.send(content=header, embeds=batch)
    return True

@tasks.loop(time=times)
async def send_daily_news():
    # เช็คเวลาปัจจุบันใน Log 
    now_th = datetime.now(tz)
    logger.info(f"Task เริ่มทำงานอัตโนมัติ ณ เวลาไทย: {now_th.strftime('%H:%M')}")
    
    articles = await fetch_news(max_articles=5)
    
    if articles:
        success = await send_news_to_discord(articles)
        if success:
            logger.info("ส่งข่าวตามเวลารอบปัจจุบันสำเร็จ")
    else:
        logger.info("ถึงเวลาส่งข่าว แต่ไม่มีข่าวใหม่ (อาจจะถูกส่งไปแล้วด้วยคำสั่งมือ)")

# ============ UI: RECRUIT SYSTEM ============
class RecruitView(discord.ui.View):
    def __init__(self, target_count, author):
        super().__init__(timeout=None)
        self.target_count = target_count
        self.participants = []
        self.author = author

    @discord.ui.button(label="⚔️ เข้าร่วมกองกำลัง", style=discord.ButtonStyle.green, custom_id="join_battle")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in [p.id for p in self.participants]:
            return await interaction.response.send_message("ท่านอยู่ในกองกำลังแล้ว!", ephemeral=True)

        self.participants.append(interaction.user)
        count = len(self.participants)
        mentions = "\n".join([f"{i+1}. {p.mention}" for i, p in enumerate(self.participants)])

        embed = discord.Embed(
            title="⚔️ การระดมพลอัศวิน",
            description=f"แม่ทัพ {self.author.mention} ต้องการ: **{self.target_count}** นาย\n\n**รายชื่อ:**\n{mentions}",
            color=discord.Color.brand_green() if count >= self.target_count else discord.Color.gold()
        )

        if count >= self.target_count:
            button.disabled = True
            button.label = "กองกำลังเต็มแล้ว"
            await interaction.response.edit_message(content="🎯 **ภารกิจระดมพลเสร็จสิ้น!**", embed=embed, view=self)
            await interaction.followup.send(f"📢 ท่านแม่ทัพ {self.author.mention}! กองกำลังครบจำนวนแล้ว!")
        else:
            await interaction.response.edit_message(embed=embed, view=self)

# ============ COMMANDS ============
@bot.tree.command(name="ระดมพล", description="เรียกเหล่านักรบมารวมตัวกัน")
async def recruit_army(interaction: discord.Interaction, จำนวนคน: int):
    if จำนวนคน < 2:
        return await interaction.response.send_message("ต้องระดมพลอย่างน้อย 2 คน!", ephemeral=True)
    
    view = RecruitView(จำนวนคน, interaction.user)
    embed = discord.Embed(
        title="⚔️ การระดมพลอัศวิน",
        description=f"ท่าน {interaction.user.mention} กำลังรวมกองกำลัง **{จำนวนคน}** นาย!",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='ข่าว', description="ดึงข่าวสารล่าสุดมาแสดงทันที")
async def manual_news(interaction: discord.Interaction): 
    try:
        # 1. แจ้ง Discord ว่ากำลังประมวลผล (ป้องกัน Error: Interaction Responded)
        await interaction.response.defer() 
        
        # 2. ดึงข่าวใหม่ (กำหนดให้ดึง 5 ข่าวล่าสุด)
        articles = await fetch_news(max_articles=5)
        
        if articles:
            # 3. ส่งข่าวไปยัง Channel ที่ตั้งค่าไว้ (หรือจะส่งกลับที่ช่องเดิมก็ได้)
            success = await send_news_to_discord(articles)
            await interaction.followup.send("ข้าไปสืบข่าวมาแปะที่กระดานให้เจ้าแล้ว!")
        else:
            await interaction.followup.send("ℹ️ ตอนนี้ยังไม่มีข่าวใหม่ๆ เข้ามาเลยครับ ท่านเจ้าเมือง")
            
    except Exception as e:
        logger.error(f"Error in manual_news: {e}")
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}")
        

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    try:
        # Sync เฉพาะตอนเปิดเครื่อง (แนะนำให้ใช้คำสั่ง Sync แยกในโปรเจกต์ใหญ่)
        await bot.tree.sync()
        if not send_daily_news.is_running():
            send_daily_news.start()
    except Exception as e:
        send_daily_news.restart()
        logger.error(f"Sync error: {e}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(CHANNEL_W)
    if channel:
        await channel.send(f"ยินดีต้อนรับสู่ปาร์ตี้วังหลวง {member.mention}! ไทเฮาหอมกำลังรอท่านอยู่ 🍵")

server_on()
bot.run(os.getenv("TOKEN"))
