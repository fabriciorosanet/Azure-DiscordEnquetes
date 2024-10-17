import discord
from discord.ext import commands
import pandas as pd
from pytz import timezone
from datetime import datetime
import asyncio
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Variável de ambiente obtida diretamente do sistema
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # O token já está configurado no portal do Azure
senha = os.getenv('EMAIL_PASSWORD')  # Buscará a senha configurada nas variáveis de ambiente


intents = discord.Intents.all()  # Habilita todas as permissões que o bot pode ter
bot = commands.Bot(command_prefix='!', intents=intents)  # Cria uma instância do bot

responses_data = []  # Lista que armazena as respostas das enquetes
saopaulo_tz = timezone('America/Sao_Paulo')  # Define o fuso horário de São Paulo

# Estrutura para as enquetes e botões
class PollButton(discord.ui.Button):
    def __init__(self, label, custom_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        # Registra a resposta do usuário quando o botão for clicado
        responses_data.append({
            "User": interaction.user.name,
            "Response": self.label,
            "Poll Datetime": datetime.now().astimezone(saopaulo_tz)
        })
        await interaction.response.send_message(f'Você votou: {self.label}', ephemeral=True)

class PollView(discord.ui.View):
    def __init__(self, options, timeout=None):
        super().__init__(timeout=timeout)
        for i, option in enumerate(options):
            self.add_item(PollButton(label=option, custom_id=f"poll_option_{i+1}"))

    async def on_timeout(self):
        # Quando a enquete expirar, desativa todos os botões
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)  # Atualiza a mensagem no Discord para refletir os botões desativados
        print("Enquete encerrada.")

# Evento quando o bot estiver pronto
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print("Bot pronto para enviar enquetes!")
    
    # Envia uma enquete automática ao canal especificado com validade
    channel_id = 1113194119825735750  # Substitua pelo ID do canal de destino
    channel = bot.get_channel(channel_id)
    
    if channel:
        question = "Como você avalia o seu perfil no LinkedIn?"
        options = [
            "Excelente – Perfil completo e atrativo",
            "Bom – Perfil sólido, espaço para melhorias",
            "Regular – Precisa de algumas atualizações",
            "Precisa de Melhorias – Várias melhorias necessárias",
            "Não Tenho LinkedIn"]

        # Define o tempo de validade (em segundos) - neste caso, 1000 segundos
        poll_duration = 1000
        view = PollView(options, timeout=poll_duration)
        
        # Envia a enquete para o canal
        view.message = await channel.send(f"**{question}**", view=view)
        
        # Inicia um temporizador para encerrar a enquete após o tempo definido
        await asyncio.sleep(poll_duration)
        
        # Após o tempo expirar, desativa os botões (feito automaticamente pelo método `on_timeout`)
        print(f"Enquete de {poll_duration} segundos encerrada.")
    else:
        print("Canal não encontrado. Verifique o ID.")

# Função para enviar o arquivo CSV por email
def enviar_email_com_anexo(destinatario, assunto, corpo, anexo_path):
    remetente = "fabriciorosafiap@gmail.com"
    senha = os.getenv('EMAIL_PASSWORD')  # Certifique-se de que a senha esteja configurada como variável de ambiente

    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Subject'] = assunto

    msg.attach(MIMEText(corpo, 'plain'))

    # Anexando o arquivo CSV
    attachment = open(anexo_path, "rb")
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(anexo_path)}")
    msg.attach(part)

    # Conectar ao servidor e enviar o email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        text = msg.as_string()
        server.sendmail(remetente, destinatario, text)
        server.quit()
        print("Email enviado com sucesso!")
    except Exception as e:
        print(f"Falha ao enviar email: {e}")

# Comando para salvar as respostas no CSV e enviar por email
@bot.command(name="salvar_respostas")
async def save_responses(ctx):
    if responses_data:
        df = pd.DataFrame(responses_data)
        df.sort_values(by="Poll Datetime", ascending=False, inplace=True)
        csv_path = 'respostas_enquete.csv'
        df.to_csv(csv_path, sep='§', encoding='utf-8', index=False)
        await ctx.send("Respostas salvas no arquivo 'respostas_enquete.csv'.")
        
        # Envia o CSV por email
        destinatario = "eduardo.bortoli@alura.com.br"
        assunto = "Respostas da enquete"
        corpo = "Segue em anexo o arquivo CSV com as respostas da última enquete."
        enviar_email_com_anexo(destinatario, assunto, corpo, csv_path)
    else:
        await ctx.send("Nenhuma resposta registrada ainda.")

bot.run(DISCORD_TOKEN)
