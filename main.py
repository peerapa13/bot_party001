import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from MSV import server_on
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix=" ", intents=intents)

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
# ============ SYSTEM ============
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"\n✅ Sync สำเร็จ! ทั้งหมด {len(synced)} คำสั่ง")
        print(f"🤖 {bot.user} พร้อมรับใช้ราชวัง!")
    except Exception as e:
        print(f"❌ Sync Error: {e}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1487069779125862551)
    text = f"ยินดีต้อนรับสู่ ปาร์ตี้วังหลวง, {member.mention} ! ไทเฮาหอมกำลังรอ {member.mention} อยู่"
    await  channel.send(text)

def main():
    
    try:
        server_on()
        bot.run(os.getenv("TOKEN"))
    except Exception as e:
        print(f"❌ ไม่สามารถรันบอทได้: {e}")

if __name__ == "__main__":
    main()