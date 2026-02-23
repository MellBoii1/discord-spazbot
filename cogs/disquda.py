import asyncio
import json
import os
import math
import platform
import random
import aiohttp
import discord
import typing
import requests
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
USER_DATA_FILE = "userdata.json"

class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, data, format_time, pretty_name,
                 difficulty="all", sort_mode="best"):
        super().__init__(timeout=120)

        self.ctx = ctx
        self.data = data
        self.format_time = format_time
        self.pretty_name = pretty_name

        self.difficulty = difficulty
        self.sort_mode = sort_mode

        self.levels = self.filter_levels()
        self.page = 0
        self.per_page = 3
        self.max_page = max(0, math.ceil(len(self.levels) / self.per_page) - 1)
        self.add_item(DifficultySelect())

    # ----------------------------
    # Filtering logic
    # ----------------------------

    def filter_levels(self):
        if self.difficulty == "all":
            return list(self.data.items())

        filtered = []
        for level, entries in self.data.items():
            if level.startswith("Easy:") and self.difficulty == "easy":
                filtered.append((level, entries))
            elif level.startswith("Default:") and self.difficulty == "hard":
                filtered.append((level, entries))

        return filtered

    # ----------------------------
    # Embed builder
    # ----------------------------

    def build_embed(self):
        embed = discord.Embed(
            title="BombSquda Co-op Best Times",
            color=0x41ab4d
        )

        start = self.page * self.per_page
        end = start + self.per_page
        page_levels = self.levels[start:end]

        for level, entries in page_levels:
            if not entries:
                continue

            reverse = self.sort_mode == "worst"
            sorted_entries = sorted(
                entries.items(),
                key=lambda x: x[1],
                reverse=reverse
            )

            lines = []
            for i, (player, time) in enumerate(sorted_entries[:5], start=1):
                lines.append(
                    f"**{i}. {player}** — `{self.format_time(time)}`"
                )

            embed.add_field(
                name=self.pretty_name(level),
                value="\n".join(lines),
                inline=False
            )

        embed.set_footer(
            text=f"Page {self.page+1}/{self.max_page+1} | "
                 f"Filter: {self.difficulty.title()} | "
                 f"Sort: {self.sort_mode.title()}"
        )

        return embed
        
    @discord.ui.button(emoji="<a:darrow_left_big:1474535619798499352>", style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(emoji="<a:arrow_left:1463262102545236170>", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(emoji="<a:arrow_right:1463262135806328965>", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(emoji="<a:darrow_right_big:1474535621216305302>", style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.max_page
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )
        
    @discord.ui.button(label="Toggle Sort", style=discord.ButtonStyle.green)
    async def toggle_sort(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_mode = "worst" if self.sort_mode == "best" else "best"

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )
        
class DifficultySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="All", value="all"),
            discord.SelectOption(label="Easy", value="easy"),
            discord.SelectOption(label="Hard", value="hard"),
        ]

        super().__init__(
            placeholder="Filter Difficulty",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        view.difficulty = self.values[0]
        view.levels = view.filter_levels()
        view.page = 0
        view.max_page = max(
            0, math.ceil(len(view.levels) / view.per_page) - 1
        )

        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view
        )
        
class Disquda(commands.Cog, name="CrossSquda"):
    def __init__(self, bot) -> None:
        self.bot = bot
        
    # ------------------ DATA LOADER PART FUCKIN 2 ---------------------
    def load_user_data(self):
        if not os.path.exists(USER_DATA_FILE):
            return {}
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_user_data(self, data):
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_user(self, uid):
        data = self.load_user_data()
        return data.setdefault(str(uid), {})

    def set_user_value(self, uid, key, value):
        data = self.load_user_data()
        user = data.setdefault(str(uid), {})
        user[key] = value
        self.save_user_data(data)
    # ------------------ DATA LOADER PART FUCKIN 2 --------------------- 
    
    def format_time(self, t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)

        if h > 0:
            return f"{h:02}:{m:02}:{s:02}:{ms:03}"
        else:
            return f"{m:02}:{s:02}:{ms:03}"

    def pretty_level_name(self, name: str) -> str:
        # Replace difficulty prefix
        if name.startswith("Default:"):
            name = "Hard: " + name[len("Default:"):]
        elif name.startswith("Easy:"):
            name = "Easy: " + name[len("Easy:"):]

        # Remove internal suffix
        if name.endswith("_squdaPB"):
            name = name[:-8]

        # Replace underscores with spaces
        return name.replace("_", " ")
        
    @commands.hybrid_command(
        name="time_leaderboard",
        description="show the leaderboard for best times on co-op levels"
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def leaderboard(self, context: Context):
        url = "https://bombsquda.tailc76b25.ts.net/get/all"

        try:
            timeout = aiohttp.ClientTimeout(total=5)  # don't hang forever
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await context.send("failed to fetch leaderboard")
                        return

                    data = await resp.json()

        except aiohttp.ClientConnectorError:
            await context.send(
                "leaderboard server is currently offline. try again later."
            )
            return

        except asyncio.TimeoutError:
            await context.send(
                "leaderboard server took too long to respond."
            )
            return

        except aiohttp.ClientError as e:
            # any other HTTP-related issue
            await context.send("failed to fetch leaderboard.")
            print(f"[Leaderboard error] {e}")
            return

        # ---------------- normal logic continues ----------------

        if not data:
            await context.send("No scores yet!")
            return
        view = LeaderboardView(
            context,
            data,
            self.format_time,
            self.pretty_level_name
        )

        await context.send(
            embed=view.build_embed(),
            view=view
        )   
    
    @commands.hybrid_command(
        name="link_bombsquda",
        description=(
            "links your BombSquda ID to your discord"
            "PS. ONLY USE IN DMS!!"
        )
    )
    async def link_bombsquda(self, ctx, bs_id: str):
        # basic sanity check
        if ctx.guild is not None:
            await ctx.send("please run this command in DMs!")
            return
        if ":" not in bs_id or len(bs_id) < 20:
            await ctx.send("that doesn't look like a ID.")
            return

        self.set_user_value(ctx.author.id, "squda_id", bs_id)
        await ctx.send(
            (
                "the id was successfully linked!\nPS. don't share it to anyone, "
                "or they could control certain things!"
            )
        )
    
    @commands.hybrid_command(
        name="unlink_bombsquda",
        description="removes the ID that you linked to your discord account."
    )
    async def unlink_bombsquda(self, ctx):
        self.set_user_value(ctx.author.id, "squda_id", None)
        await ctx.send("done! the previous ID was removed.")

async def setup(bot) -> None:
    await bot.add_cog(Disquda(bot))