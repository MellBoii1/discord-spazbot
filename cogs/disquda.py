import asyncio
import json
import os
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
        url = "https://bombsquda-leaderboard.tailc76b25.ts.net/get/all"

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

        embed = discord.Embed(
            title="Leaderboard",
            color=0x41ab4d
        )

        for level, entries in data.items():
            if not entries:
                continue

            sorted_entries = sorted(entries.items(), key=lambda x: x[1])

            lines = []
            for i, (player, time) in enumerate(sorted_entries[:5], start=1):
                lines.append(f"**{i}. {player}** — `{self.format_time(time)}`")

            embed.add_field(
                name=self.pretty_level_name(level),
                value="\n".join(lines),
                inline=False
            )

        await context.send(embed=embed)       
    
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