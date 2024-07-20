import json
import random
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
import copy

class GachaHandle:
    def load_shards(self):
        self.shards_dict = {}
        self.shards_rarities = {}
        self.options = []
        self.collection_counts = {}
        self.total_shards = 0
        with open("options.json", "r") as rarities:
            all_options = json.loads(rarities.read())
            total = 0
            to_infer_prob = None
            for option in all_options:
                parsed_chance = float(option["chance"])
                self.options.append((option["rarity"], parsed_chance))
                if parsed_chance == -1:
                    to_infer_prob = len(self.options)-1
                else:
                    total += parsed_chance

            self.options[to_infer_prob] = (self.options[to_infer_prob][0], 1-total)
            self.options.sort(key=lambda x: x[1])
            print("Loaded rarities: " + str(self.options))
        
        with open("shards.json", "r") as shards_json:
            all_shards = json.loads(shards_json.read())

            for shard in all_shards:
                #Increase shard count and add it to collection counts
                if shard["collection"] not in self.collection_counts:
                    self.collection_counts[shard["collection"]] = 0
                self.collection_counts[shard["collection"]] += 1
                self.total_shards += 1
                
                # Add to shards_dict
                self.shards_dict[shard["id"]] = shard

                # Add to shards_rarities
                if shard["rarity"] not in self.shards_rarities:
                    self.shards_rarities[shard["rarity"]] = []    
                self.shards_rarities[shard["rarity"]].append(shard["id"])

            print(self.shards_dict, self.shards_rarities, "Have been loaded.")

    def get_gacha_option(self):
        pull = random.random()
        total = 0
        i = -1
        while pull > total:
            i += 1
            total += self.options[i][1]
            

        #print(self.options[i][0] + " was selected.")

        selected_rarity = self.options[i][0]
        given_item = random.choice(self.shards_rarities[selected_rarity])
        return given_item

    # Please do not modify the returned values. That would not be nice.
    def get_info(self, item):
        return self.shards_dict[item]

    def get_collections(self):
        return self.collection_counts

class UserHandle:
    def __init__(self):
        self.HOURS = 4.5
        self.gacha_handle = GachaHandle()
        self.gacha_handle.load_shards()
        
    def load_users(self):
        self.users = {}

        with open("users.json", "r") as users_json:
            try:
                self.users = json.loads(users_json.read())
            except JSONDecodeError:
                print("We failed to load json data for users. This is probably bad.")

    def user_init(self, user_id):
        # Place all necessary fields if not present
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {}
        if "last_wish_time" not in self.users[user_id]:
            self.users[user_id]["last_wish_time"] = datetime.strftime(datetime.now() - timedelta(hours=10*self.HOURS), "%y-%m-%d %H:%M:%S")
        if "wish_amount" not in self.users[user_id]:
            self.users[user_id]["wish_amount"] = "0"
        if "inventory" not in self.users[user_id]:
            self.users[user_id]["inventory"] = {}
        if "collections" not in self.users[user_id]:
            self.users[user_id]["collections"] = {}
        if "total_items" not in self.users[user_id]:
            self.users[user_id]["total_items"] = 0

    def user_gacha(self, user_id):
        user_id = str(user_id)
        

        # Determine the time elapsed since the user cast a wish
        last_time = datetime.strptime(self.users[user_id]["last_wish_time"], "%y-%m-%d %H:%M:%S")
        time_elapsed = datetime.now() - last_time

        # Calculate wishes generated
        wishes = float(self.users[user_id]["wish_amount"])
        wishes += time_elapsed.total_seconds() / (3600*self.HOURS)
        wishes = min(wishes, 10)
        
        # Update the wish count and wish time
        self.users[user_id]["last_wish_time"] = datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S")
        self.users[user_id]["wish_amount"] = str(wishes)

        # If we have a wish, proceed
        if wishes >= 1:
            print("Wish is ready. Commencing sequence.")

            # Update the wish count after wishing
            wishes -= 1
            self.users[user_id]["wish_amount"] = str(wishes)

            # Acquire the item
            item = self.gacha_handle.get_gacha_option()
            if item not in self.users[user_id]["inventory"]:
                self.users[user_id]["inventory"][item] = 0

                # Increase collection count if this is the first of that item
                collection = self.gacha_handle.get_info(item)["collection"]
                if collection not in self.users[user_id]["collections"]:
                    self.users[user_id]["collections"][collection] = 0
                self.users[user_id]["collections"][collection] += 1

                self.users[user_id]["total_items"] += 1
                
            self.users[user_id]["inventory"][item] += 1

            return (True, self.gacha_handle.get_info(item))
        else:
            # Give the time at which one wish will be available (at a rate of 8 hours per wish)
            return (False, datetime.now() + timedelta(hours=self.HOURS)*(1-wishes))

    def wishes(self, user_id):
        user_id = str(user_id)
        return self.users[user_id]["wish_amount"]

    def collections(self, user_id):
        user_id = str(user_id)

        my_collections = copy.copy(self.users[user_id]["collections"])
        all_collections = self.gacha_handle.get_collections()
        for collection_name in all_collections:
            if collection_name in my_collections:
                my_collections[collection_name] = (my_collections[collection_name], all_collections[collection_name])
            else:
                my_collections[collection_name] = (0, all_collections[collection_name])

        return my_collections
            
        

    def save_users(self):
        with open("users.json", "w") as users_json:
            users_json.write(json.dumps(self.users, indent=4))
