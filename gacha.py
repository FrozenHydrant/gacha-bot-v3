import json
import random
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
import copy
import util
from pynoise.noisemodule import Perlin
from pynoise.noiseutil import noise_map_plane
import numpy as np
import os
from threading import Lock
import yt_dlp

class GachaHandle:
    def load_shards(self):
        random.seed()
        
        self.shards_dict = {}
        self.shards_rarities = {}
        self.options = {}
        self.collection_counts = {}
        self.collections_dict = {}
        self.rarities_dict = {}
        self.currencies_dict = {}
        self.abilities_dict = {}
        self.total_shards = 0
        with open("options.json", "r") as rarities:
            all_options = json.loads(rarities.read())
            to_infer_prob = None
            for option in all_options["rarities"]:
                parsed_chance = float(option["chance"])
                self.rarities_dict[option["rarity"]] = option
                self.options[option["rarity"]] = parsed_chance
                
            print("Loaded rarities: " + str(self.options), self.rarities_dict, "\n")

            # Initialize collections
            for collection in all_options["collections"]:
                self.collection_counts[collection["id"]] = 0
                self.collections_dict[collection["id"]] = collection

            for currency in all_options["currencies"]:
                self.currencies_dict[currency["id"]] = currency

            print("Loaded currencies: ", self.currencies_dict)
        
        with open("shards.json", "r") as shards_json:
            all_shards = json.loads(shards_json.read())

            for shard in all_shards:
                #Increase shard count and add it to collection counts
                self.collection_counts[shard["collection"]] += 1
                self.total_shards += 1
                
                # Add to shards_dict
                self.shards_dict[shard["id"]] = shard

                # Add to shards_rarities
                if shard["rarity"] not in self.shards_rarities:
                    self.shards_rarities[shard["rarity"]] = []    
                self.shards_rarities[shard["rarity"]].append(shard["id"])

            print(self.shards_dict, self.shards_rarities, " have been loaded.\n")
            print(self.collection_counts, self.collections_dict, " have also been loaded.\n")
            print("In total", self.total_shards, "shards have been loaded.")

        with open("abilities.json", "r") as abilities_json:
            self.abilities_dict = json.loads(abilities_json.read())
            print(self.abilities_dict, " has been loaded.\n")

    def infer_rarities_to_list(self, options):
        user_options = copy.copy(options)
        to_infer_rarity = None
        accumulated_chance = 0
        for option in user_options:
            if user_options[option] >= 0:
                accumulated_chance += user_options[option]
            else:
                to_infer_rarity = option

        if to_infer_rarity is not None:
            user_options[to_infer_rarity] = 1-accumulated_chance

        user_options_list = []
        for option in user_options:
            user_options_list.append((option, user_options[option]))
        user_options_list.sort(key=lambda x: x[1])

        return user_options_list
    
    def get_gacha_option(self, avoid, overrides, mults):
        user_options = copy.copy(self.options)

        for override in overrides:
            user_options[override] = overrides[override]

        for mult in mults:
            user_options[mult] *= mults[mult]

        user_options_list = self.infer_rarities_to_list(user_options)
        print("User's options:", user_options_list, " Global options:", self.options)
        
        # But why not?
        random.seed()
        
        pull = random.random()
        total = 0
        i = -1
        while pull > total:
            i += 1
            total += user_options_list[i][1]
            
        selected_rarity = user_options_list[i][0]
        item_pool = copy.copy(self.shards_rarities[selected_rarity])
        for item in avoid:
            if item in item_pool:
                item_pool.remove(item)

        if len(item_pool) > 0:        
            given_item = random.choice(item_pool)
        else:
            given_item = random.choice(self.shards_rarities[selected_rarity])
        return given_item

    def get_id_from_name(self, name):
        for item in self.shards_dict:
            if name.lower() in self.get_item_info(item)["name"].lower():
                return item
        return None

    def has_ability(self, item_id):
        if item_id in self.abilities_dict:
            return True
        return False

    def get_ability(self, item_id):
        return copy.copy(self.abilities_dict[item_id])
    
    # Please do not modify the returned values. That would not be nice.
    def get_item_info(self, item):
        if item not in self.shards_dict:
            return None
        return copy.copy(self.shards_dict[item])

    def get_collection_info(self, collection):
        return copy.copy(self.collections_dict[collection])

    def get_collections(self):
        return copy.copy(self.collection_counts)

    def get_rarity_info(self, rarity):
        return copy.copy(self.rarities_dict[rarity])

    def get_rarities(self):
        counts = {}
        for rarity in self.shards_rarities:
            counts[rarity] = len(self.shards_rarities[rarity])
        return counts

    def get_currency_info(self, currency):
        return copy.copy(self.currencies_dict[currency])

    def get_currencies(self):
        return copy.copy(self.currencies_dict)

    def get_rarity_tiers(self):
        return self.infer_rarities_to_list(self.options)

class SongHandle:
    def __init__(self):
        # Taken from yt_dlp github
        self.ydl_opts = {
            'format': 'm4a/bestaudio/best',
            # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
            'postprocessors': [{  # Extract audio using ffmpeg
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'outtmpl': 'song/%(id)s.%(ext)s'
        }
        self.ydl = yt_dlp.YoutubeDL(self.ydl_opts)
        self.song_info = {}
        self.song_lock = Lock()

        # Load song info from disk
        try:
            with open(os.path.join(os.getcwd(), "song", "song_info.json"), "r") as song_info_file:
                self.song_info = json.loads(song_info_file.read())
        except:
            print("Error loading song info. Maybe none exists, or file is cooked.")

    def _save_song_info(self):
        with self.song_lock:
            try:
                song_save_file = open(os.path.join(os.getcwd(), "song", "song_info.json"), "x")
            except:
                song_save_file = open(os.path.join(os.getcwd(), "song", "song_info.json"), "w")
            song_save_file.write(json.dumps(self.song_info))
            song_save_file.close()
    
    def _download_song(self, info):
        name_of_file = info['id'] + "." + info['audio_ext']
        if os.path.exists(os.path.join(os.getcwd(), "song", name_of_file)):
            print(name_of_file, " exists. Not downloading.")
            return True

        if info['duration_string'].count(":") >= 2:
            print(name_of_file, "is too long. Not considering it.")
            return False

        try:
            self.ydl.download(info['original_url'])

            # Add relevant info to songs_info json file
            important_info = {"id": info["id"], "title": info["title"], "duration": info["duration_string"], "url": info["original_url"], "uses": 0}
            if "channel" in info:
                important_info["channel"] = info["channel"]
            elif "uploader" in info:
                important_info["channel"] = info["uploader"]
            with self.song_lock:
                self.song_info[info["id"]] = important_info

            # Save the song
            self._save_song_info()
            
            return True
        except Exception as e:
            # Delete leftovers
            if os.path.exists(os.path.join(os.getcwd(), "song", info['id']+".m4a")):
                os.remove(os.path.join(os.getcwd(), "song", info['id']+".m4a"))
            print('An unknown problem occured while downloading.', e)
            return False

    def _download_url(self, user_id, user_playlist, url):
        with self.ydl:
            try:
                successful_downloads = 0
                info = self.ydl.sanitize_info(self.ydl.extract_info(url, download=False))

                # Check if playlist or just one song
                if "entries" not in info:
                    # Just one song
                    success = self._download_song(info)
                    if success:
                        if info['id'] not in user_playlist["songs"]:
                            successful_downloads += 1
                            user_playlist["songs"].append(info['id'])
                            with self.song_lock:
                                self.song_info[info['id']]['uses'] += 1
                else:
                    # Entire playlist
                    for song in info["entries"]:
                        success = self._download_song(song)
                        if success:
                            if song['id'] not in user_playlist["songs"]:
                                successful_downloads += 1
                                user_playlist["songs"].append(song['id'])
                                with self.song_lock:
                                    self.song_info[song['id']]['uses'] += 1

                # Try saving the song info again
                self._save_song_info()
                
                # TODO: Threadsafe
                try:
                    playlist_file = open(os.path.join(os.getcwd(), "playlist", user_id+".json"), "x")
                except:
                    playlist_file = open(os.path.join(os.getcwd(), "playlist", user_id+".json"), "w")
                #print(playlist_file)
                playlist_file.write(json.dumps(user_playlist))
                #print(json.dumps(user_playlist))
                playlist_file.close()
                return successful_downloads
            except yt_dlp.utils.DownloadError:
                print("Download failed for the url", url)
                return 0

    def download(self, ctx, url):
        user_id = str(ctx.author.id)
        try:
            with open(os.path.join(os.getcwd(), "playlist", user_id+".json"), "r") as playlist_file:
                user_playlist = json.loads(playlist_file.read())
        except:
            user_playlist = {"songs": []}

        return {"ctx": ctx, "count": self._download_url(user_id, user_playlist, url)}
                    
    def info_test(self, url):
        with self.ydl:
            output = None
            try:
                output = open('test_song_output.txt', 'x')
            except:
                output = open('test_song_output.txt', 'w')
                
            info = self.ydl.sanitize_info(self.ydl.extract_info(url, download=False))
            #print('Got song with information:', info['audio_ext'], info['id'])
            output.write(json.dumps(info))
            output.close()
            
class UserHandle:
    def __init__(self):
        self.perlin = Perlin()
        self.HOURS = 3.5
        
        self.gacha_handle = GachaHandle()
        self.gacha_handle.load_shards()

        self.users_lock = Lock()

        with open("phrases.json", "r") as phrases_json:
            phrases = json.loads(phrases_json.read())
            self.phrases = phrases["phrases"]
        
    def load_users(self):
        self.users = {}

        saves_directory = os.path.join(os.getcwd(), "users")
        for savefile in os.listdir(saves_directory):
            user_id = savefile.split(".")[0]
            with open(os.path.join(saves_directory, savefile), "r") as user_info:
                try:
                    user_dict = json.loads(user_info.read())
                    self.users[user_id] = user_dict
                except JSONDecodeError:
                    print("We failed to load json data for person", savefile, ". This could be bad.")
                    
        #with open("users.json", "r") as users_json:
        #    try:
        #        self.users = json.loads(users_json.read())
        #    except JSONDecodeError:
        #        print("We failed to load json data for users. This is probably bad.")

    def user_init(self, user_id):
        # Place all necessary fields if not present
        user_id = str(user_id)
        with self.users_lock:
            compensated = 0
            if user_id not in self.users:
                self.users[user_id] = {}
            if "last_wish_time" not in self.users[user_id]:
                self.users[user_id]["last_wish_time"] = datetime.strftime(datetime.now() - timedelta(hours=10*self.HOURS), "%y-%m-%d %H:%M:%S")
            if "wish_amount" not in self.users[user_id]:
                self.users[user_id]["wish_amount"] = 0
            if "inventory" not in self.users[user_id]:
                self.users[user_id]["inventory"] = {}

            # Version control: nonexistent
            self.users[user_id]["wish_amount"] = float(self.users[user_id]["wish_amount"])

            ### More inventory management #############
            to_remove = []
            for item in self.users[user_id]["inventory"]:
                item_info = self.gacha_handle.get_item_info(item)

                if item_info is None:
                    compensated += self.users[user_id]["inventory"][item]
                    to_remove.append(item)

            self.users[user_id]["wish_amount"] += compensated

            while len(to_remove) > 0:
                item_to_remove = to_remove.pop()
                self.users[user_id]["inventory"].pop(item_to_remove)
            ### End of More Inventory Management ######
            ###########################################
                        
            if "collections" not in self.users[user_id]:
                self.users[user_id]["collections"] = {}

                # Initialize collections
                for item in self.users[user_id]["inventory"]:
                    item_info = self.gacha_handle.get_item_info(item)

                    if item_info["collection"] not in self.users[user_id]["collections"]:
                        self.users[user_id]["collections"][item_info["collection"]] = 0
                    self.users[user_id]["collections"][item_info["collection"]] += 1
            if "world" not in self.users[user_id]:
                self.users[user_id]["world"] = {}

                self.users[user_id]["world"]["exists"] = False
            if "total_items" not in self.users[user_id]:
                self.users[user_id]["total_items"] = 0
            if "statuses" not in self.users[user_id]:
                self.users[user_id]["statuses"] = {}
            if "selected" not in self.users[user_id]:
                self.users[user_id]["selected"] = ""
            if "sparkles" not in self.users[user_id]:
                self.users[user_id]["sparkles"] = 0
            if "gears" not in self.users[user_id]:
                self.users[user_id]["gears"] = 0
            if "haloes" not in self.users[user_id]:
                self.users[user_id]["haloes"] = 0
            if "sprinkles" not in self.users[user_id]:
                self.users[user_id]["sprinkles"] = 0

            for item in self.users[user_id]["inventory"]:
                if item not in self.users[user_id]["statuses"]:
                    self.users[user_id]["statuses"][item] = {"name": "Available"}

            return compensated

    def update_wishes(self, user_id):
        user_id = str(user_id)

        # Determine the time elapsed since the user cast a wish
        last_time = datetime.strptime(self.users[user_id]["last_wish_time"], "%y-%m-%d %H:%M:%S")
        time_elapsed = datetime.now() - last_time

        # Calculate wishes generated
        wishes = float(self.users[user_id]["wish_amount"])
        wishes += min(time_elapsed.total_seconds() / (3600*self.HOURS), 10)
        
        # Update the wish count and wish time
        self.users[user_id]["last_wish_time"] = datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S")
        self.users[user_id]["wish_amount"] = wishes

        return wishes

    def user_gacha(self, user_id):
        user_id = str(user_id)

        with self.users_lock:
            wishes = self.update_wishes(user_id)
            # If we have a wish, proceed
            if wishes >= 1:
                wish_compensated = False
                print("Wish is ready. Commencing sequence.")

                # Acquire the item
                item = self.gacha_handle.get_gacha_option(list(self.users[user_id]["inventory"].keys()), {}, {})

                if item not in self.users[user_id]["inventory"]:
                    self.users[user_id]["inventory"][item] = 0

                    # Increase collection count if this is the first of that item
                    collection = self.gacha_handle.get_item_info(item)["collection"]
                    if collection not in self.users[user_id]["collections"]:
                            self.users[user_id]["collections"][collection] = 0
                    self.users[user_id]["collections"][collection] += 1

                    self.users[user_id]["total_items"] += 1
                    wishes -= 1
                else:
                    wishes -= 0.5
                    wish_compensated = True

                # Update the wish count and inventory after wishing
                self.users[user_id]["wish_amount"] = wishes
                self.users[user_id]["inventory"][item] += 1

                item_info = self.gacha_handle.get_item_info(item)
                collection_name = self.gacha_handle.get_collection_info(item_info["collection"])["name"]

                return (True, item_info, collection_name, wish_compensated)
            else:
                # Give the time at which one wish will be available (at a rate of 3.5 hours per wish)
                return (False, datetime.now() + timedelta(hours=self.HOURS)*(1-wishes), None, None)

    def select(self, user_id, item):
        user_id = str(user_id)
        
        selected_item_id = self.gacha_handle.get_id_from_name(item)

        if selected_item_id == None:
            return None

        if selected_item_id not in self.users[user_id]["inventory"]:
            return None
                
        return self.gacha_handle.get_item_info(selected_item_id)
        

    def wishes(self, user_id):
        user_id = str(user_id)
        return self.users[user_id]["wish_amount"]

    def collections(self, user_id):
        user_id = str(user_id)

        with self.users_lock:
            my_collections = copy.copy(self.users[user_id]["collections"])
            all_collections = self.gacha_handle.get_collections()
            collections_info = {}
            for collection_id in all_collections:
                collection_name = self.gacha_handle.get_collection_info(collection_id)["name"]
                if collection_id in my_collections:
                    collections_info[collection_name] = (my_collections[collection_id], all_collections[collection_id])
                else:
                    collections_info[collection_name] = (0, all_collections[collection_id])

        #print(collections_info)
        return collections_info

    def update_item_status(self, user_id, item):
        user_id = str(user_id)
        statuses = self.users[user_id]["statuses"]
        if statuses[item]["name"] == "Available":
            return None
        time_left = datetime.strptime(statuses[item]["until"], "%y-%m-%d %H:%M:%S") - datetime.now()
        if time_left.days < 0:
            statuses[item]["name"] = "Available"
            return None
        
        return time_left


    def get_amount_rarity_owned(self, user_id, rarity):
        user_id = str(user_id)
        inventory = self.users[user_id]["inventory"]
        amount = 0
        for item in inventory:
            item_info = self.gacha_handle.get_item_info(item)
            if item_info["rarity"] == rarity:
                amount += 1
        return amount
            

    def itemslist(self, user_id):
        user_id = str(user_id)

        with self.users_lock:
            statuses = self.users[user_id]["statuses"]
            texts = {}
            all_rarities = self.gacha_handle.get_rarities()
            to_remove = []
            for item in statuses:
                time_left = self.update_item_status(user_id, item)
                item_info = self.gacha_handle.get_item_info(item)
                # Inventory management
                if item_info is None:
                    to_remove.append(item)
                # End of inventory management
                else:
                    item_text = ""
                    if time_left is not None:
                        item_text = item_info["name"] + " (x" + str(self.users[user_id]["inventory"][item]) + ") - **" + statuses[item]["name"] + " (" + util.timeformat(time_left, "d", "h", "m") + ")**"
                    else:
                        # Crazy string mechanics
                        if self.gacha_handle.has_ability(self.gacha_handle.get_item_info(item)["id"]):
                            item_text = "Special Ability "
                        item_text = self.gacha_handle.get_item_info(item)["name"] + " (x" + str(self.users[user_id]["inventory"][item]) + ") - **" + item_text + statuses[item]["name"] + "**"

                    item_text += "\n"

                    item_rarity = item_info["rarity"]
                    if item_rarity not in texts:
                        texts[item_rarity] = "__**" + item_rarity + " (" + str(self.get_amount_rarity_owned(user_id, item_rarity)) + "/" + str(all_rarities[item_rarity]) + ")**__\n"
                    texts[item_rarity] += item_text
                    
            for item in to_remove:
                statuses.pop(item)
            
            totality = ""
            for paragraph in texts.values():
                totality += paragraph + "\n"
                
        return totality

    def ability(self, user_id, item_name):
        user_id = str(user_id)

        with self.users_lock:
            ability_item = self.select(user_id, item_name)
            if ability_item == None:
                return ("Invalid item name supplied.", False)
            
            if not self.gacha_handle.has_ability(ability_item["id"]):
                return ("The selected unit has no ability.", False)

            # Let's avoid using an eval here.
            ability = self.gacha_handle.get_ability(ability_item["id"])

            # Update item status
            self.update_item_status(user_id, ability_item["id"])
            if self.users[user_id]["statuses"][ability_item["id"]]["name"] != "Available":
                return ("The selected unit is on cooldown.", False)

            actual_target = None
            actual_target = user_id

            for effect in ability["effects"]:
                calculated_value = 1
                for change in effect["factors"]:
                    new_value = self.users[actual_target]
                    if isinstance(change, list):
                        for thing in change:
                            if thing in new_value:
                                new_value = new_value[thing]
                            else:
                                new_value = 1
                                break
                    else:
                        new_value = change
                    calculated_value *= new_value

                to_change = self.users[actual_target]
                for select in effect["path"]:
                    to_change = to_change[select]
                to_change[effect["value"]] = float(to_change[effect["value"]])
                to_change[effect["value"]] += calculated_value
                
                #print(calculated_value)
                    
            
            self.users[user_id]["statuses"][ability_item["id"]]["name"] = "Cooldown"
            self.users[user_id]["statuses"][ability_item["id"]]["until"] = datetime.strftime(datetime.now() + timedelta(hours=ability["cooldown"]), "%y-%m-%d %H:%M:%S")
        return ("Successfully used " + ability_item["name"] + "'s ability and placed them on a " + str(ability["cooldown"]) + "h cooldown.", True) 

    def get_available_items(self, user_id):
        new_inventory = []
        user_id = str(user_id)
        for item in self.users[user_id]["inventory"]:
            self.update_item_status(user_id, item)
            if self.users[user_id]["statuses"][item]["name"] == "Available":
                new_inventory.append(item)

        return new_inventory

    def vivify(self, element):
        if element < -0.25:
            return ":blue_square:"
        elif element < -0.05:
            return ":yellow_square:"
        elif element < 0.2:
            return ":green_square:"
        elif element < 0.35:
            return ":mountain:"
        return ":mountain_snow:"

    def create_land_claim(self, user_id):
        user_id = str(user_id)
        random.seed()
        x = None
        z = None
        with self.users_lock:
            if not self.users[user_id]["world"]["exists"]:
                self.users[user_id]["world"]["x"] = random.randrange(0, 1000000)
                self.users[user_id]["world"]["z"] = random.randrange(0, 1000000)
            x = self.users[user_id]["world"]["x"]
            z = self.users[user_id]["world"]["z"]
            self.users[user_id]["world"]["exists"] = True
        noisemap = self.calculate_tiles(x, z)
        vivification = np.vectorize(self.vivify)
        noisemap = vivification(noisemap)

        output = ""
        for i in noisemap:
            for j in i:
                output += j
            output += "\n"
        return output
        

    def calculate_stability(self, user_id):
        user_id = str(user_id)
        
        new_inventory = self.get_available_items(user_id)
        if len(self.users[user_id]["inventory"]) == 0:
            return 0
        return (len(new_inventory) - 2) / len(self.users[user_id]["inventory"])

    def attack(self, attacker_id, attacker_name, defender_id, defender_name):
        attacker_id = str(attacker_id)
        defender_id = str(defender_id)

        with self.users_lock:
            attack_inventory = self.get_available_items(attacker_id)
            defense_inventory = self.get_available_items(defender_id)

            attack_stability = self.calculate_stability(attacker_id)
            defense_stability = self.calculate_stability(defender_id)

            if len(attack_inventory) < 1:
                return (attacker_name + " had no units. What a shame.", "", {})
            if len(defense_inventory) < 1:
                if len(self.users[defender_id]["inventory"]) < 1:
                    return (defender_name + " can't defend themselves.", "", {})
                else:
                    return (defender_name + " can't defend themselves.", "", {})

            attack_lives = 5
            defense_lives = 5
            totally = ""

            # Initialize the given loot with all possible loots
            given_loot = {}

            # Shuffle the lists, based on https://stackoverflow.com/questions/10048069/what-is-the-most-pythonic-way-to-pop-a-random-element-from-a-list
            random.shuffle(attack_inventory)
            random.shuffle(defense_inventory)
            
            while attack_lives > 0 and defense_lives > 0 and len(attack_inventory) > 0 and len(defense_inventory) > 0:
                # Get the attacking unit, defending unit, and amount of both
                attack_unit = self.gacha_handle.get_item_info(attack_inventory.pop())
                defense_unit = self.gacha_handle.get_item_info(defense_inventory.pop())
                attack_amount = self.users[attacker_id]["inventory"][attack_unit["id"]]
                defense_amount = self.users[defender_id]["inventory"][defense_unit["id"]]

                attack_strength = self.gacha_handle.get_rarity_info(attack_unit["rarity"])["strength"] * attack_amount
                defense_strength = self.gacha_handle.get_rarity_info(defense_unit["rarity"])["strength"] * defense_amount

                true_attack_strength = (random.random() * (1-attack_stability) + attack_stability) * attack_strength
                true_defense_strength = (random.random() * (1-defense_stability) + defense_stability) * defense_strength

                #print(attack_unit["name"], defense_unit["name"], attack_strength, defense_strength, attack_stability, defense_stability, true_attack_strength, true_defense_strength) 
                phrase = random.choice(self.phrases)
                win = None
                win_unit = None
                win_amount = None
                loss = None
                loss_unit = None
                loss_amount = None
                if true_attack_strength > true_defense_strength:
                    win = attacker_name
                    win_unit = attack_unit["name"]
                    win_amount = attack_amount
                    loss = defender_name
                    loss_unit = defense_unit["name"]
                    loss_amount = defense_amount
                    defense_lives -= 1
                    self.users[defender_id]["statuses"][defense_unit["id"]]["name"] = "Damaged"
                    self.users[defender_id]["statuses"][defense_unit["id"]]["until"] = datetime.strftime(datetime.now() + timedelta(hours=1), "%y-%m-%d %H:%M:%S")

                    # Award loot for slain enemies
                    self.users[attacker_id][self.gacha_handle.get_collection_info(defense_unit["collection"])["currency"]] += self.gacha_handle.get_rarity_info(defense_unit["rarity"])["strength"]
                    currency_name = self.gacha_handle.get_currency_info(self.gacha_handle.get_collection_info(defense_unit["collection"])["currency"])["name"]
                    if currency_name not in given_loot:
                        given_loot[currency_name] = 0
                    given_loot[currency_name] += self.gacha_handle.get_rarity_info(defense_unit["rarity"])["strength"]
                    
                else:
                    loss = attacker_name
                    loss_unit = attack_unit["name"]
                    loss_amount = attack_amount
                    win = defender_name
                    win_unit = defense_unit["name"]
                    win_amount = defense_amount
                    attack_lives -= 1
                    self.users[attacker_id]["statuses"][attack_unit["id"]]["name"] = "Damaged"
                    self.users[attacker_id]["statuses"][attack_unit["id"]]["until"] = datetime.strftime(datetime.now() + timedelta(hours=1), "%y-%m-%d %H:%M:%S")

                totally += "**" + win + "'s " + win_unit + " -> " + loss + "'s " + loss_unit + "**\n"    
                totally += phrase.replace("<win>", win).replace("<win_unit>", win_unit + "**x**" + str(win_amount)).replace("<loss>", loss).replace("<loss_unit>", loss_unit + "**x**" + str(loss_amount))
                totally += "\n\n"

            winning_person = None
            if defense_lives < attack_lives:
                winning_person = attacker_name + " wins"
            else:
                winning_person = defender_name + " wins"
            
        return (totally, winning_person, given_loot)

    def calculate_tiles(self, x, z):
        random.seed(2)
        noisemap = np.array(noise_map_plane(width=12, height=12, lower_x=x, upper_x=x+1, lower_z=z, upper_z=z+1, source=self.perlin)).reshape(12, 12)
        return noisemap
            

    def save_by_id(self, user_id):
        user_id = str(user_id)

        with self.users_lock:
            write_directory = os.path.join(os.getcwd(), "users")
            save_path = os.path.join(write_directory, user_id+".json")
            if os.path.exists(save_path):
                with open(save_path, "w") as save_file:
                    save_file.write(json.dumps(self.users[user_id], indent=4))
            else:
                with open(save_path, "x") as save_file:
                    save_file.write(json.dumps(self.users[user_id], indent=4))

        
    def save_users(self):
        # https://www.geeksforgeeks.org/python-os-path-exists-method/
        for user_id in self.users:
            self.save_by_id(user_id)
