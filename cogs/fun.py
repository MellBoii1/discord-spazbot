import json # FIXME: maybe use a alternative to json?
import os
import platform
import random
import time
import aiohttp
import discord
import typing
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

DATA_FILE = "userdata.json"
# note; ALWAYS use this variable since
# everytime a emoji gets updated on 
# discord, it's markdown changes
TICKETS_EMOJI = "<:spaztix:1470673170427285608>"
TOKENS_EMOJI = "<:spaztokens:1470673171618336809>"
FUN_FACTS = [
    "spaz tickets and tokens are both heavily based on Gummy's Overhaul's gumcoins and gumdollars, and the usual tickets and tokens",
    "(bombsquda) hitting a player on the head with a bomb INSTANTLY kills them,\nalong with giving you some tickets",
    "the tickets are purple because im purple :troll:",
    "i'm eating ram right now!",
    "buddie-bot is my twinny twin twin ong",
    (
        "spazbot, the leaderboard, and bombsquda itself is "
        "completely open source!\nyou can check them out using the links below."
        "\nhttps://github.com/MellBoii1/bombsquda-server"
        "\nhttps://github.com/MellBoii1/discord-spazbot"
        "\nhttps://github.com/MellBoii1/bombsquda"
    ),
    
]
RANDOM_GETTICKETS = [
    "you robbed a random bank and got {tickets} {e}tickets.",
    "you found {tickets} {e}tickets on the ground, and took em for yourself.\n...jeez, thats a lot",
    "you beat the hell up of a passer-by and took {tickets} {e}tickets (rude!)",
    "you hacked spazbot and gave yourself {tickets} {e}tickets.",
    "you actually worked hard (instead of robbing people) and earned {tickets} {e}tickets!",
    "i gave you {tickets} {e}tickets because you seem cool.",
    "you opened a chest which had {tickets} {e}tickets.",
    "you begged on the streets for tickets and someone gave you {tickets} {e}tickets.",
    "you commited tax fraud and got away with {tickets} {e}tickets.",
    "you took a bunch of tickets from the theater and painted them green ({tickets} {e}tickets)",
    "you won a tournament for {tickets} {e}tickets! (gee, i wonder what game it was)",
    "you traded some money for {tickets} {e}tickets! (probably not a good investment)",
]
OUTCOMES = [
    {
        "check": lambda v: v < 0,
        "msg": "tough luck, you lost {v} {currency} <:newbie_bruh:1461416819809063014>",
        "sound": "audio/gamble_bad.wav",
        "kinds": {"normal"},
    },
    {
        "check": lambda v: v == 0,
        "msg": "well that sucks, you got {v} {currency}. nothing.",
        "sound": "audio/gamble_bad.wav",
        "kinds": {"normal", "special"},
    },
    {
        "check": lambda v: v < 25,
        "msg": "you won {v} {currency}... well, at least it's something. <:spazsob:1462275889478766622>",
        "sound": "audio/gamble_ok.wav",
        "kinds": {"normal"},
    },
    {
        "check": lambda v: v == 69,
        "msg": "you won {v} {currency}, niiiiceee... <:absolutespaz:1461416707372482710>",
        "sound": "audio/gamble_good.wav",
        "kinds": {"normal"},
    },
    {
        "check": lambda v: v < 120,
        "msg": "well... you won {v} {currency}. not shabby. <:newbie_shrug:1461560562604441600>",
        "sound": "audio/gamble_ok.wav",
        "kinds": {"normal"},
    },
    {
        "check": lambda v: True,
        "msg": "wowza, you won {v} {currency}!! <:newbie_OK:1461416821860208741>",
        "sound": "audio/gamble_good.wav",
        "kinds": {"normal"},
    },
    {
        "check": lambda v: True,
        "msg": "hell yeah, you won {v} {currency}!!! <:newbie_OK:1461416821860208741>",
        "sound": "audio/gamble_good.wav",
        "kinds": {"special"},
    },
]
CURRENCIES = {
    "tickets": {
        "display": f"{TICKETS_EMOJI} tickets",
        "emoji": TICKETS_EMOJI,
        "min_cost": 50,
        "chance": 0.83,
        "range": (-275, 270),
        "jackpot": True,
        "jackpot_bonus": (500, 800),
        "kind": "normal",
    },

    "tokens": {
        "display": f"{TOKENS_EMOJI} tokens",
        "emoji": TOKENS_EMOJI,
        "min_cost": 0,
        "chance": 0.13,
        "range": (0, 20),
        "jackpot_bonus": (3, 10),
        "jackpot": True,
        "kind": "special",
    },
}
ROB_CURRENCIES = {
    "tickets": {
        "display": f"{TICKETS_EMOJI} tickets",
        "chance": 0.9,
        "min_required": 250,
        "range": (100, 250),

        "success": "you successfully stole {v} {TICKETS_EMOJI} tickets from {target}!",
        "fail": (
            "{target} caught you trying to rob them and...\n"
            "..beat you up i guess. they robbed you of {v} {TICKETS_EMOJI} tickets instead."
        ),
    },

    "tokens": {
        "display": f"{TOKENS_EMOJI} tokens",
        "chance": 0.1,
        "min_required": 15,
        "range": (4, 10),

        "success": "wow! you took {v} {TOKENS_EMOJI} tokens from {target}.\ndon't think they'll be happy about that..",
        "fail": (
            "you horribly failed... and then {target} noticed and stole {v} {TOKENS_EMOJI} tokens from YOU."
        ),
    },
}
JACKPOT = {
    "chance": 0.1,
    "range": (400, 880),
    "prefix": "🎰JACKPOT!!🎰 ",
    "sound": "audio/jackpot.wav",
}

ROB_MULTI_DURATION = 1200  # 20 minutes in seconds

SHOP_ITEMS = {
    "tokens": {
        "price": 1000,
        "currency": "tickets",
        "description": "Trade 1000 tickets for a token.",
        "effect": lambda self, user_id, amount: self.add_value(user_id, "tokens", amount)
    },
    "tickets": {
        "price": 1,
        "currency": "tokens",
        "description": "Trade 1 token for 1000 tickets.",
        "effect": lambda self, user_id, amount: self.add_value(user_id, "tickets", 1000 * amount)
    },
    "title: ULTRAGAMBLER": {
        "price": 4000,
        "currency": "tickets",
        "description": "Unlock the title 'ULTRAGAMBLER' for your profile.",
        "extradesc": "This will multiply the amount of money you get **(and lose)** from gambling by 2, and jackpot chance by 15%",
        "effect": lambda self, user_id, amount: self.set_value(user_id, "title", "ULTRAGAMBLER")
    },
    "title: Addicted to Gambling": {
        "price": 8000,
        "currency": "tickets",
        "description": "Unlock the title 'Addicted to Gambling'",
        "extradesc": "This will multiply the amount of money you get **(and lose)** from gambling by 3, and jackpot chance by 20%",
        "effect": lambda self, user_id, amount: self.set_value(user_id, "title", "Addicted to Gambling")
    },
    "title: Total SpazBot Enthusiast": {
        "price": 12000,
        "currency": "tickets",
        "description": "Unlock the title 'Total SpazBot Enthusiast' for your profile.",
        "extradesc": "This does not unlock any extra abilities.",
        "effect": lambda self, user_id, amount: self.set_value(user_id, "title", "Total SpazBot Enthusiast")
    },
    "rob_multiplier": {
        "price": 60,
        "currency": "tokens",
        "description": "Increases chance of successful robs by 15% for 20 minutes.",
        "effect": lambda self, user_id, amount: self.add_rob_multi(user_id)
    }
}

class CurrencyShareView(discord.ui.View):
    def __init__(self, *, author, amount, user, contexto, currency_key, currency_config, emoji):
        super().__init__(timeout=None)

        self.author = author
        self.user = user
        self.amount = amount
        self.contexto = contexto

        self.currency_key = currency_key
        self.currency_config = currency_config
        self.emoji = emoji

        self.title = f"confirmation for {self.author.display_name}"

    # ---------------- data helpers ----------------

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_value(self, user_id: int, label: str, default=0):
        data = self.load_data()
        return data.get(str(user_id), {}).get(label, default)

    def set_value(self, user_id: int, label: str, value):
        data = self.load_data()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {}
        data[uid][label] = value
        self.save_data(data)

    def add_value(self, user_id: int, label: str, amount: int):
        current = self.get_value(user_id, label, 0)
        self.set_value(user_id, label, current + amount)
        return current + amount

    # ---------------- buttons ----------------

    @discord.ui.button(
        label="",
        style=discord.ButtonStyle.green,
        emoji="<a:thumbsup:1462624450964095202>",
        custom_id="currency_share_yes",
    )
    async def yep(self, interaction: discord.Interaction, button: discord.ui.Button):
        # user pressing button is not the author
        if interaction.user != self.author:
            await interaction.response.send_message(
                "get outta here stupid.",
                ephemeral=True
            )
            return
        # proceed with the whole gist
        embed = discord.Embed(
            title=self.title,
            description=(
                f"{self.user.mention} was given "
                f"{self.amount} {self.emoji} {self.currency_key}!"
            ),
            color=discord.Color.green()
        )
        # send the user's mention (so they get notified)
        await self.contexto.send(self.user.mention)
        await interaction.response.edit_message(embed=embed)
        # add (and remove) the values
        self.add_value(self.user.id, self.currency_key, self.amount)
        self.add_value(self.author.id, self.currency_key, -self.amount)
        self.stop()

    @discord.ui.button(
        label="",
        style=discord.ButtonStyle.red,
        emoji="<a:thumbsdown:1462932503001039014>",
        custom_id="currency_share_no",
    )
    async def nope(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.author:
            await interaction.response.send_message(
                "get outta here stupid.",
                ephemeral=True
            )
            return
        # user has pressed us; cancel
        embed = discord.Embed(
            title=self.title,
            description=(
                f"request to give {self.user.display_name} "
                f"{self.amount} {self.emoji} {self.currency_key} was cancelled."
            ),
            color=discord.Color.red()
        )
        # edit
        await interaction.response.edit_message(embed=embed)
        self.stop()


class LeaderboardView(discord.ui.View):
    def __init__(self, *, stat, sorted_users, bot, guild, total_pages, current_page=0):
        super().__init__(timeout=300)

        self.stat = stat
        self.sorted_users = sorted_users
        self.bot = bot
        self.guild = guild
        self.total_pages = total_pages
        self.current_page = current_page

        self.update_buttons()

    def update_buttons(self):
        # Enable/disable buttons based on current page
        self.children[0].disabled = self.current_page == 0  # Previous
        self.children[1].disabled = self.current_page == self.total_pages - 1  # Next

    def get_embed(self):
        start = self.current_page * 5
        end = start + 5
        page_users = self.sorted_users[start:end]

        lines = []
        for i, (user_id, info) in enumerate(page_users, start=start + 1):

            member = self.guild.get_member(int(user_id)) if self.guild else None
            user = member or self.bot.get_user(int(user_id))

            name = user.display_name if member else (
                user.name if user else f"User {user_id}"
            )

            lines.append(f"**{i}. {name}** — {info[self.stat]}")

        embed = discord.Embed(
            title=f"🏆 {self.stat.capitalize()} Leaderboard (Page {self.current_page + 1}/{self.total_pages})",
            description="\n".join(lines) if lines else "No entries on this page.",
            color=discord.Color.gold()
        )

        return embed

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="<a:arrow_left:1463262102545236170>")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="<a:arrow_right:1463262135806328965>")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)


class Fun(commands.Cog, name="Fun"):
    def __init__(self, bot) -> None:
        self.bot = bot
        
    # --------------------------- DATA LOADER --------------------------   
    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_value(self, user_id: int, label: str, default=0):
        data = self.load_data()
        return data.get(str(user_id), {}).get(label, default)

    def set_value(self, user_id: int, label: str, value):
        data = self.load_data()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {}
        data[uid][label] = value
        self.save_data(data)

    def add_value(self, user_id: int, label: str, amount: int = 1):
        current = self.get_value(user_id, label, 0)
        self.set_value(user_id, label, current + amount)
        return current + amount

    def all_values(self, user_id: int):
        data = self.load_data()
        return data.get(str(user_id), {})
    # --------------------------- DATA LOADER --------------------------    

    def add_rob_multi(self, user_id: int):
        expirations = self.get_value(user_id, "rob_multi_expirations", [])
        if not isinstance(expirations, list):
            expirations = []
        expirations.append(time.time() + ROB_MULTI_DURATION)
        self.set_value(user_id, "rob_multi_expirations", expirations)

    def clean_expired_rob_multi(self):
        data = self.load_data()
        current_time = time.time()
        for uid, info in data.items():
            expirations = info.get("rob_multi_expirations", [])
            if isinstance(expirations, list):
                active = [exp for exp in expirations if exp > current_time]
                if active != expirations:
                    info["rob_multi_expirations"] = active
        self.save_data(data)

    @commands.hybrid_group(name="shop", description="Shop subcommands")
    async def shop(self, ctx):
        await ctx.reply('This command cannot be used by itself! Use shop list, shop buy or shop about')

    @shop.command(name="list", description="Get a list of the shop items")
    async def shop_list(self, ctx):
        items_list = "\n".join(f"**{name}**: {data['price']} {CURRENCIES[data['currency']]['emoji']} {data['currency']} - {data['description']}" for name, data in SHOP_ITEMS.items())
        embed = discord.Embed(title="Shop", description=items_list or "No items available.", color=discord.Color.blue())
        await ctx.send(embed=embed)
    
    def get_item_names():
        item_list = []

        for name in SHOP_ITEMS:  # only keys now
            choice = app_commands.Choice(name=name, value=name)
            item_list.append(choice)

        return item_list

    @shop.command(name="about", description="Get details about a shop item")
    @app_commands.choices(item=get_item_names())
    @app_commands.describe(item='The item you want to learn about')
    async def shop_about(self, ctx, item: app_commands.Choice[str]):
        item_name = item.value
        if item_name not in SHOP_ITEMS:
            await ctx.send(f"item '{item_name}' not found in the shop.")
            return
        data = SHOP_ITEMS[item_name]
        extra_desc = data.get('extradesc', '')
        embed = discord.Embed(
            title=f"About {item_name}",
            description=f"{data['description']}\n{extra_desc}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Price",
            value=f"{data['price']} {CURRENCIES[data['currency']]['emoji']} {data['currency']}"
        )
        await ctx.send(embed=embed)

    @shop.command(name="buy", description="Buy an item from the shop")
    @app_commands.choices(item=get_item_names())
    @app_commands.describe(item='The item you want to buy', amount='The amount you want to buy')
    async def shop_buy(self, ctx, item: str, amount: int = 1):
        item = item.lower()
        matched_item = next(
            (name for name in SHOP_ITEMS if name.lower() == item),
            None
        )
        if not matched_item:
            await ctx.send(f"item `{item}` not found in the shop.")
            return
        if amount <= 0:
            await ctx.send("amount must be greater than 0.")
            return
        data = SHOP_ITEMS[matched_item]
        total_price = data['price'] * amount
        balance = self.get_value(ctx.author.id, data['currency'])
        if balance < total_price:
            await ctx.send(
                f"you don't have enough {data['currency']}!\n"
                f"you need {total_price}, but you only have {balance}."
            )
            return
        # Deduct currency
        self.add_value(ctx.author.id, data['currency'], -total_price)
        # Apply effect
        if 'effect' in data and data['effect']:
            data['effect'](self, ctx.author.id, amount)
        await ctx.send(f"You successfully bought {amount} amounts of **{item}**!")

    # maybe like add some other way to gain currency later?
    @commands.hybrid_command(
        name="grind",
        description=(
            "grind and get some tickets without robbing "
            "or gambling! use this if it's your first time."
        ),
    )
    @commands.cooldown(1, 17, commands.BucketType.user)
    async def grind(self, ctx):
        value = random.randint(50, 200)
        new_total = self.add_value(ctx.author.id, "tickets", value) # add total to user data

        template = random.choice(RANDOM_GETTICKETS) # template
        message = template.format(tickets=value, e=TICKETS_EMOJI) # formatting (wow just like bombsquad's lstrs)

        await ctx.reply(message)
    
    @commands.hybrid_command(
        name="share",
        description="share a currency with your friends!",
        aliases=['give']
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def share(self, ctx, user: discord.Member, amount: str, currency: str):

        currency = currency.lower() # lower because someone certainly will use upper

        if currency not in CURRENCIES: # currency not in currencies
            await ctx.send(f"unknown currency: `{currency}`")
            return

        cfg = CURRENCIES[currency] # wow  config
        emoji = cfg["emoji"] # emoji (duh!)

        player_amount = self.get_value(ctx.author.id, currency) # wdym player? lol

        # -------- amount parsing --------

        if amount == "all": # amount is 'all'; make it all
            amount = player_amount
        elif amount == "half": # amount is 'half'; make it halved
            amount = player_amount // 2
        else:
            try:
                amount = int(amount)
            except ValueError: # value likely not a number
                await ctx.send("amount must be a number, `all`, or `half`.")
                return

        # -------- validations --------

        if amount < 1: # value is below 1 (likely negative or 0)
            await ctx.send("amount has to be positive.")
            return

        if amount > player_amount: # value above player's current balance
            await ctx.send(f"you only have {player_amount} {emoji} {currency}!")
            return

        if user == ctx.author: # attempting to give to self
            await ctx.send(f"you can't give yourself {currency}!")
            return

        if user == self.bot.user: # attempting to give to the bot
            await ctx.send("sorry, can't take those. you might wanna hold on to them.")
            ctx.command.reset_cooldown(ctx)
            return

        if user.bot: # attempting to give to some bot
            await ctx.send("that's a bot, i don't think they'd even care.")
            return

        # -------- confirmation --------

        embed = discord.Embed(
            title=f"confirmation for {ctx.author.display_name}",
            description=(
                f"do you want to share {amount} "
                f"{emoji} {currency} with {user.display_name}?"
            ),
            color=discord.Color.greyple()
        )

        await ctx.send(
            embed=embed,
            view=CurrencyShareView(
                author=ctx.author,
                amount=amount,
                user=user,
                contexto=ctx,
                currency_key=currency,
                currency_config=cfg,
                emoji=emoji,
            )
        )
        
    def roll_rob_currency(self):
        r = random.random()
        total = 0.0
        for name, data in ROB_CURRENCIES.items():
            total += data["chance"]
            if r <= total:
                return name, data
        return "tickets", ROB_CURRENCIES["tickets"]
        
    @commands.hybrid_command(
        name="rob",
        description=(
            "rob your friends of their money!"
            " however you can also get caught and lose money"
        ),
        aliases=['steal']
    )
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def rob(self, ctx, user: discord.Member):

        # ---------------------------- situations ----------------------------------------
        if ctx.guild is None: # if server is not anything
            await ctx.send("there's no one here, other than you and me...")
            ctx.command.reset_cooldown(ctx)
            return

        if user == ctx.author: # if user is themselves
            await ctx.send("that's called 'taking money out of your wallet'. not 'robbing'.")
            ctx.command.reset_cooldown(ctx)
            return

        if user == self.bot.user: # if user is us
            await ctx.send("bold of you to tell me to do that...")
            ctx.command.reset_cooldown(ctx)
            return

        if user.bot: # if user is a bot
            await ctx.send("that's a bot. i don't think they even have money.")
            ctx.command.reset_cooldown(ctx)
            return
        # -------------------------------------------------------------------------------
        # get a random currency from our rob func
        # (and also the display name)
        currency, cdata = self.roll_rob_currency()
        display = cdata["display"]

        # Balance checks
        # user's currency is below the minimum
        if self.get_value(ctx.author.id, currency) < cdata["min_required"]:
            await ctx.send(f"you need at least {cdata['min_required']} {display} to try that.")
            ctx.command.reset_cooldown(ctx)
            return
        # target user's currency is below the minimum
        if self.get_value(user.id, currency) < cdata["min_required"]:
            await ctx.send(f"hey come on, they don't even have {cdata['min_required']} {display}!")
            ctx.command.reset_cooldown(ctx)
            return
        value = random.randint(*cdata["range"])
        chance = 0.45 # more in favor of failing
        expirations = self.get_value(ctx.author.id, "rob_multi_expirations", [])
        current_time = time.time()
        active = [exp for exp in expirations if exp > current_time]
        multiplier = len(active) * 0.15
        self.set_value(ctx.author.id, "rob_multi_expirations", active)
        if random.random() < chance + multiplier:
            msg = cdata["success"].format(v=value, target=user.mention, TICKETS_EMOJI=TICKETS_EMOJI, TOKENS_EMOJI=TOKENS_EMOJI,)
            self.add_value(ctx.author.id, currency, value)
            self.add_value(user.id, currency, -value)
        else: # we absolutely failed
            msg = cdata["fail"].format(v=value, target=user.mention, TICKETS_EMOJI=TICKETS_EMOJI, TOKENS_EMOJI=TOKENS_EMOJI,)
            self.add_value(ctx.author.id, currency, -value)
            self.add_value(user.id, currency, value)
        # now just reply i guess
        await ctx.reply(msg)
            
    def roll_currency(self):
        r = random.random()
        total = 0.0
        for name, data in CURRENCIES.items():
            total += data["chance"]
            if r <= total:
                return name, data
        return "tickets", CURRENCIES["tickets"]
        
    @commands.hybrid_command(
        name="gamble",
        description="gamble for some stuff!"
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def gamble(self, ctx):
        currency, cdata = self.roll_currency()
        display = cdata["display"]
        kind = cdata.get("kind", "normal")

        # Cost check (only really matters for tickets)
        if cdata["min_cost"] > 0:
            balance = self.get_value(ctx.author.id, currency)
            if balance < cdata["min_cost"]:
                await ctx.send(
                    f"hey hang on, you need at least {cdata['min_cost']} {display}!"
                )
                ctx.command.reset_cooldown(ctx)
                return
        # Base value
        value = random.randint(*cdata["range"])
        jackpot = False
        # More stats based on current title
        extraval = 0
        title = self.get_value(ctx.author.id, 'title')
        if title == 'ULTRAGAMBLER':
            extraval = 0.15
        if title == 'Addicted to Gambling':
            extraval = 0.20
        if cdata.get("jackpot", False):
            jackpot = random.random() < JACKPOT["chance"] + extraval
            if jackpot:
                bonus = random.randint(*cdata["jackpot_bonus"])
                value += bonus
        if title == 'ULTRAGAMBLER':
            value *= 2
        if title == 'Addicted to Gambling':
            value *= 3
        for outcome in OUTCOMES:
            if kind not in outcome["kinds"]:
                continue

            if outcome["check"](value):
                msg = outcome["msg"].format(
                    v=value,
                    currency=cdata["display"],
                    TICKETS_EMOJI=TICKETS_EMOJI,
                    TOKENS_EMOJI=TOKENS_EMOJI,
                )
                break

        if jackpot: # add prefix if needed
            msg = JACKPOT["prefix"] + msg

        self.add_value(ctx.author.id, currency, value)
        await ctx.reply(msg)

    # FIXME: this command is a joke
    # if we release spazbot publically, we should 
    # probably remove it entirely
    @commands.hybrid_command(
        name="goon", 
        description="what the fuck."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def goon(self, ctx):
        await ctx.reply('https://tenor.com/view/sigeon-pex-sigeon-gif-8909686852464980802')
    
    @commands.hybrid_command(
        name="fun_fact", 
        description="get a random fun fact, whether it be of bombsquda, the bot, or whatnot!"  
    )
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def fun_fact(self, ctx):
        msg = f"fun fact: {random.choice(FUN_FACTS)}"
        await ctx.send(msg)

    @commands.hybrid_command(
        name="stats",
        description="get all stats you have!",
        aliases=['balance', 'bal']
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx, user: discord.User = None):
        actuser = user or ctx.author
        # jeez, is there ANY better way to do this??
        is_self = user is None
        your = "Your" if is_self else f"{actuser.display_name}'s"
        you = "You" if is_self else actuser.display_name
        have_has = "have" if is_self else "has"

        values = self.all_values(actuser.id)
        if not values:
            await ctx.send(f"{you} {have_has} no stats yet.")
            return

        HIDDEN_STATS = {"admin", "squda_id", "rob_multi_expirations"} # hide confidential stats

        # Filter visible stats only
        visible_stats = {
            k: v for k, v in values.items()
            if k not in HIDDEN_STATS
        }
        # user has nothin
        if not visible_stats:
            await ctx.send(f"{you} {have_has} no public stats yet.")
            return
        # join all dem items into a nice list
        text = "\n".join(f"**{k}**: {v}" for k, v in visible_stats.items())
        await ctx.reply(f"{your} stats:\n{text}")
        
    def get_cur_names():
        item_list = []

        for name in CURRENCIES:  # only keys now
            choice = app_commands.Choice(name=name, value=name)
            item_list.append(choice)
        return item_list
        
    @commands.hybrid_command(
        name="leaderboard",
        description="see whoever has the most of a stat!",
        aliases=["lb"]
    )
    @app_commands.choices(
        stat=get_cur_names(),
    )
    @app_commands.describe(stat='Filter a specific currency/stat', server_only='Filter only this server?')
    async def leaderboard(self, ctx, stat: str = "tickets", server_only: bool = False):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        if server_only:
            if not ctx.guild:
                await ctx.send("This filter only works inside servers.")
                return

            guild_member_ids = {str(member.id) for member in ctx.guild.members}

            data = {
                uid: info
                for uid, info in data.items()
                if uid in guild_member_ids
            }

        # Filter users that actually have the stat
        filtered = {
            uid: info for uid, info in data.items()
            if stat in info
        }

        if not filtered:
            await ctx.send(f"No one has the stat `{stat}`!")
            return

        sorted_users = sorted(
            filtered.items(),
            key=lambda x: x[1][stat],
            reverse=True
        )

        total_pages = (len(sorted_users) + 4) // 5

        view = LeaderboardView(
            stat=stat,
            sorted_users=sorted_users,
            bot=self.bot,
            guild=ctx.guild,
            total_pages=total_pages,
            current_page=0
        )

        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)

async def setup(bot) -> None:
    await bot.add_cog(Fun(bot))