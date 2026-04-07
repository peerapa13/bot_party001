import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from MSV import server_on
import feedparser
import asyncio
from datetime import datetime
import logging
# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
 
# ตั้งค่า Discord Bot
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="/", intents=intents)

CHANNEL_New = int(os.getenv("CHANNEL_New", 0))
CHANNEL_W = int(os.getenv("CHANNEL_W", 0))
#=========ข่าว============
# แหล่งข่าว
NEWS_SOURCES = [
    {
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "name": "Bloomberg News"
    },
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "name": "Reuters Business"
    },
    {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "name": "Ars Technica"
    },
    {
        "url": "https://feeds.techcrunch.com/",
        "name": "TechCrunch"
    },
    {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "name": "BBC News"
    },
]
# ตัวแปรเก็บข่าวที่ส่งไปแล้ว
sent_articles = set()
async def fetch_news(max_articles=5):
    """ดึงข่าวจากแหล่งข้อมูลต่างๆ"""
    all_articles = []
    
    for source in NEWS_SOURCES:
        try:
            logger.info(f"📡 กำลังดึงข่าวจาก {source['name']}...")
            feed = feedparser.parse(source['url'])
            
            # ดึงบทความจากแหล่งนี้
            for entry in feed.entries:
                article = {
                    'title': entry.get('title', 'ไม่มีหัวข้อ'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', 'ไม่มีสรุป'),
                    'source': source['name'],
                    'published': entry.get('published', datetime.now().isoformat()),
                }
                
                # ตรวจสอบว่ามี link และไม่ได้ส่งไปแล้ว
                if article['link'] and article['link'] not in sent_articles:
                    all_articles.append(article)
                
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการดึงข่าวจาก {source['name']}: {e}")
    
    # จัดเรียงและเลือก 5 อันดับแรก
    all_articles = all_articles[:max_articles]
    logger.info(f"✅ พบข่าวใหม่ {len(all_articles)} เรื่อง")
    
    return all_articles
 
async def send_news_to_discord(articles):
    """ส่งข่าวไปยัง Discord Channel"""
    try:
        channel = bot.get_channel(CHANNEL_New)
        
        if channel is None:
            logger.error(f"❌ ไม่พบ Channel ID: {CHANNEL_New}")
            return False
        
        if not articles:
            logger.info("ℹ️ ไม่มีข่าวใหม่ที่ต้องส่ง")
            return False
        
        # สร้าง Embed สำหรับข่าวแต่ละเรื่อง
        embeds = []
        
        for i, article in enumerate(articles, 1):
            # ทำให้ title มีความยาวเหมาะสม
            title = article['title'][:250]
            
            # ทำให้ summary มีความยาวเหมาะสม
            summary = article['summary']
            if len(summary) > 400:
                summary = summary[:397] + "..."
            
            # ลบแท็ก HTML ออก (ถ้ามี)
            summary = summary.replace('<[^<]+?>', '')
            
            embed = discord.Embed(
                title=f"📰 {title}",
                url=article['link'],
                description=summary,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"🏢 {article['source']}")
            
            embeds.append(embed)
            sent_articles.add(article['link'])
        
        # ส่งข่าว (Discord มีขีดจำกัด 10 embeds ต่อ message)
        chunks = [embeds[i:i+10] for i in range(0, len(embeds), 10)]
        
        for i, batch in enumerate(chunks):
            if i == 0:
                # ส่ง message ตัวแรกพร้อมชื่อเรื่อง
                message_text = f"📰 **ข่าวประจำวัน {datetime.now().strftime('%d/%m/%Y')} เวลา %H:%M น.**"
                await channel.send(message_text, embeds=batch)
            else:
                await channel.send(embeds=batch)
        
        logger.info(f"✅ ส่งข่าว {len(embeds)} เรื่องไปยัง Discord สำเร็จ")
        return True
            
    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาดในการส่งข่าวไปยัง Discord: {e}")
        return False
 
@tasks.loop(hours=24)
async def send_daily_news():
    """ส่งข่าวทุกวันเวลา 6 โมงเช้า"""
    try:
        logger.info("⏰ เริ่มการดึงและส่งข่าวประจำวัน...")
        articles = await fetch_news(max_articles=5)
        
        if articles:
            success = await send_news_to_discord(articles)
            if success:
                logger.info("✅ ส่งข่าวประจำวันสำเร็จ")
        else:
            logger.warning("⚠️ ไม่พบข่าวใหม่")
    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาดในการส่งข่าวประจำวัน: {e}")
 
@send_daily_news.before_loop
async def before_send_news():
    """รอให้บอท ready และคำนวณเวลารอจนถึง 6 โมงเช้า"""
    await bot.wait_until_ready()
    
    now = datetime.now()
    target_time = now.replace(hour=6, minute=0, second=0, microsecond=0)
    
    # ถ้าเวลาผ่าน 6 โมงแล้ว ให้รอจนถึงวันพรุ่งนี้
    if now >= target_time:
        from datetime import timedelta
        target_time += timedelta(days=1)
    
    wait_seconds = (target_time - now).total_seconds()
    
    logger.info(f"⏳ รอจนถึง {target_time.strftime('%H:%M:%S')} ({int(wait_seconds)} วินาที)")
    await asyncio.sleep(wait_seconds)
 

# ============ UI COMPONENTS ============
class RecruitView(discord.ui.View):
    def __init__(self, target_count, author):
        super().__init__(timeout=None)
        self.target_count = target_count
        self.participants = [] # เก็บเป็น List ของ User Objects
        self.author = author

    @discord.ui.button(label="⚔️ เข้าร่วมกองกำลัง", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรวจสอบว่าซ้ำไหม
        if interaction.user.id in [p.id for p in self.participants]:
            await interaction.response.send_message("ท่านได้เข้าร่วมกองกำลังนี้อยู่แล้ว!", ephemeral=True)
            return

        # เพิ่มผู้เข้าร่วม
        self.participants.append(interaction.user)
        current_count = len(self.participants)
        
        # ✅ สร้างรายชื่อแบบ Mention (@username)
        names = "\n".join([f"{idx+1}. {p.mention}" for idx, p in enumerate(self.participants)])
        
        embed = discord.Embed(
            title="⚔️ การระดมพลอัศวิน",
            description=f"แม่ทัพ **{self.author.mention}** ต้องการกำลังพล: **{self.target_count}** นาย\n\n**รายชื่อผู้ตอบรับ:**\n{names}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"ความคืบหน้า: {current_count}/{self.target_count}")

        if current_count >= self.target_count:
            # เมื่อครบจำนวน: ปิดปุ่ม
            button.disabled = True
            button.label = "กำลังพลครบแล้ว"
            button.style = discord.ButtonStyle.grey
            
            await interaction.response.edit_message(content="🎯 **ภารกิจระดมพลเสร็จสิ้น!**", embed=embed, view=self)
            # แจ้งเตือนแม่ทัพ
            await interaction.followup.send(f"📢 แจ้งท่านแม่ทัพ {self.author.mention}! ขณะนี้กองกำลังครบ **{self.target_count}** นาย พร้อมออกศึกแล้ว!")
        else:
            # ถ้ายังไม่ครบ: อัปเดต Embed ปกติ
            await interaction.response.edit_message(embed=embed, view=self)

# ============ SLASH COMMANDS ============
@bot.tree.command(name="ระดมพล", description="เรียกเหล่านักรบมารวมตัวกันด้วยชื่อ")
@app_commands.describe(จำนวนคน="จำนวนคนที่ต้องการระดมพล")
async def recruit_army(interaction: discord.Interaction, จำนวนคน: int):
    if จำนวนคน <= 1:
        await interaction.response.send_message("การระดมพลต้องมีอย่างน้อย 2 นายขึ้นไป!", ephemeral=True)
        return

    embed = discord.Embed(
        title="⚔️ การระดมพลอัศวิน",
        description=f"ท่าน **{interaction.user.mention}** กำลังรวบรวมกองกำลังจำนวน **{จำนวนคน}** นาย!\n\n*(กดปุ่มด้านล่างเพื่อรายงานตัว)*",
        color=discord.Color.gold()
    )
    
    view = RecruitView(target_count=จำนวนคน, author=interaction.user)
    await interaction.response.send_message(embed=embed, view=view)

@bot.command(name='ข่าว')
async def manual_news(ctx):
    """คำสั่ง /ข่าว เพื่อดึงข่าวด้วยตนเอง"""
    try:
        # แสดงการโหลด
        loading_msg = await ctx.send("⏳ กำลังดึงข่าว... (อาจใช้เวลาสักครู่)")
        articles = await fetch_news(max_articles=5)
        
        if articles:
            await send_news_to_discord(articles)
            await loading_msg.edit(content="✅ ส่งข่าวสำเร็จ!")
        else:
            await loading_msg.edit(content="❌ ไม่พบข่าวใหม่")
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")

# ============ SYSTEM ============
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"\n✅ Sync สำเร็จ! ทั้งหมด {len(synced)} คำสั่ง")
        print(f"🤖 {bot.user} พร้อมรับใช้ราชวัง!")
        
        # เริ่มการส่งข่าวประจำวัน
        if not send_daily_news.is_running():
            send_daily_news.start()
            logger.info("✅ เริ่มตัวจับเวลาส่งข่าวประจำวันสำเร็จ")
    except Exception as e:
        print(f"❌ Sync Error: {e}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(CHANNEL_W)
    text = f"ยินดีต้อนรับสู่ ปาร์ตี้วังหลวง, {member.mention} ! ไทเฮาหอมกำลังรอ {member.mention} อยู่"
    await  channel.send(text)

server_on()
bot.run(os.getenv("TOKEN"))
