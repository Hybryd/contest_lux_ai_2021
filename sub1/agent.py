from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math
import sys
import random

DIRECTIONS = Constants.DIRECTIONS
game_state = None

# HELPER FUNCTIONS

### Define helper functions

def is_in_map(pos):
    x = pos.x
    y = pos.y
    w, h = game_state.map.width, game_state.map.height
    
    return (x<w)&(y<w)&(x>=0)&(y>=0)

# Redefine Position.direction_to to avoid citytiles
def direction_to_avoid_citytiles(unit, game_state, target_pos):
        """
        Return closest position to target_pos from this position, if it is not a citytile (except target_pos)
        """
        DIRECTIONS = Constants.DIRECTIONS

        check_dirs = [
            DIRECTIONS.NORTH,
            DIRECTIONS.EAST,
            DIRECTIONS.SOUTH,
            DIRECTIONS.WEST,
        ]
        
        closest_dir = DIRECTIONS.CENTER
        
        i=0
        while i<4 and (unit.pos.translate(check_dirs[i], 1) != target_pos and game_state.map.get_cell_by_pos(unit.pos.translate(check_dirs[i], 1)).citytile!=None):
            i+=1
        
        
        if i<4:
            direction = check_dirs[i]
            
            newpos = unit.pos.translate(direction, 1)
            closest_dist = unit.pos.translate(check_dirs[i], 1).distance_to(target_pos)
            closest_dir = check_dirs[i]
    
            for direction in check_dirs:
                newpos = unit.pos.translate(direction, 1)
                if is_in_map(newpos):
                    if game_state.map.get_cell_by_pos(newpos) != None:
                        if newpos == target_pos or game_state.map.get_cell_by_pos(newpos).citytile==None:
    
                            dist = target_pos.distance_to(newpos)
    
                            if dist < closest_dist:
                                closest_dir = direction
                                closest_dist = dist
    
            
        return closest_dir


def get_list_of_carts(player):
    res = []
    for u in player.units:
        if u.is_cart():
            res.append(u)
    return res

# +++++++++++++++++++++++++++++++++++++++++++++++++
#   FIND RESOURCES IN THE MAP
# +++++++++++++++++++++++++++++++++++++++++++++++++
def find_resources(game_state):
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles


# +++++++++++++++++++++++++++++++++++++++++++++++++
#   FIND RESOURCES CLOSEST TO UNIT FULL OF CARGO
# +++++++++++++++++++++++++++++++++++++++++++++++++
def find_closest_resources(pos, player, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_dist:
            if (resource_tile.resource.type=='uranium') & (player.researched_uranium()): 
                closest_dist = dist
                closest_resource_tile = resource_tile
            elif (resource_tile.resource.type=='coal') & (player.researched_coal()): 
                closest_dist = dist
                closest_resource_tile = resource_tile
            elif (resource_tile.resource.type=='wood'):
                closest_dist = dist
                closest_resource_tile = resource_tile
    return closest_resource_tile


# +++++++++++++++++++++++++++++++++++++++++++++++++
#   FIND THE CLOSEST CITYTILE ON THE MAP
# +++++++++++++++++++++++++++++++++++++++++++++++++
def find_closest_city_tile(pos, player):
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile

# +++++++++++++++++++++++++++++++++++++++++++++++++
#   FIND THE CLOSEST CITYTILE OF THE GIVEN CITY
# +++++++++++++++++++++++++++++++++++++++++++++++++
def find_closest_city_tile_in_city(pos, player, cit):
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            if city == cit:
                for city_tile in city.citytiles:
                    dist = city_tile.pos.distance_to(pos)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_city_tile = city_tile
    return closest_city_tile


# +++++++++++++++++++++++++++++++++++++++++++++++++
#   FIND THE CLOSEST CELL IN A GIVEN LIST OF CELLS
# +++++++++++++++++++++++++++++++++++++++++++++++++
def find_closest_cell_in_list(pos, list_cells):
    closest_cell = None
    closest_dist = math.inf
    if len(list_cells) > 0:
        
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for c in list_cells:
            dist = c.pos.distance_to(pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_cell = c
    return closest_cell, closest_dist


# ===========================================
#  FIND THE TILES ADJACENT TO GIVEN POSITION
# ============================================
def adjacent_tiles(pos):
    ''' Get adjacent tiles given a tile'''
    x1,y1 = pos.x, pos.y
    w, h = game_state.map.width, game_state.map.height
    adjacent_tiles_pos = [(x1-1,y1),(x1+1,y1),(x1,y1+1),(x1,y1-1)]
    return [ game_state.map.get_cell(x,y) for (x,y) in adjacent_tiles_pos if (x<w)&(y<w)&(x>=0)&(y>=0) ]

# ==============================================================
#  FIND THE TILE TO BUILD ADJACENT TO CLOSEST CITYTILE
# ==============================================================
def building_tiles(player, pos):
    list_adjacent_cells_to_city = []
    cities = []
    for k, city in player.cities.items():
        cities.append(city.citytiles)
    
    for city in cities:
        for citytile in city:
            neighborhood = adjacent_tiles(citytile.pos) # list of Cell
            for n in neighborhood:
                if n not in list_adjacent_cells_to_city and (n.has_resource()==False) & (n.citytile==None) :
                    list_adjacent_cells_to_city.append(n)
    closest_cell, closest_dist = find_closest_cell_in_list(pos, list_adjacent_cells_to_city)       
    return closest_cell

    
def citytiles_sorted_by_fuel_capacity(pos, player):
    """
    Return the list of the closest citytiles belonging to different cities, sorted by amount of fuel available in the corresponding cities
    The number of elements of the resulting list is equal to the number of cities
    """
    res=[]
    if len(player.cities) > 0:
        for k, city in player.cities.items():
            city_tile = find_closest_city_tile_in_city(pos, player, city)
            res.append({"tile": city_tile, "fuel":city.fuel})
            
    if res!=[]:
        res= sorted(res, key=lambda x: x["fuel"], reverse=False)
    return res

# ==============================================================
#  COMPUTE TIME BEFORE NIGHTFALL
# ==============================================================
def time_before_nightfall(observation):
    """
    Returns the number of rounds before nightfall, 0 if it is the night
    """
    step = observation['step']%40
    return max(0,30-step)



# =========================================================================
#  FLOODFILL ALGORITHM TO GET THE CONNECTED CELLS OF A GIVEN CELL (SAME RESOURCE TYPE)
# =========================================================================
def floodfill(pos):
    res = []
    player_cell = game_state.map.get_cell_by_pos(pos)
    explored = [player_cell]
    to_explore = [player_cell]
    resource_type = player_cell.resource
    
    while to_explore != []:
        current_cell = to_explore.pop()
        if current_cell not in res:
            res.append(current_cell)
            neighborhood = adjacent_tiles(current_cell.pos)
            for a in neighborhood:
                if a not in explored:
                    if a.has_resource():
                        if a.resource.type == resource_type.type:
                            to_explore.append(a)
            explored.append(current_cell)
    return res

# =======================================
#  FIND ALL SETS OF RESOURCES OF THE MAP
# =======================================
def get_sets_of_resources(city_cell):
    """
    Returns a dict {closest_cell : [closest_dist, total_ressource]}
    """
    res={}
    list_sets = []
    for x in range(game_state.map.width):
        for y in range(game_state.map.height):
            current_cell = game_state.map.get_cell(x,y)
            if current_cell.has_resource() :
                if current_cell not in (item for sublist in list_sets for item in sublist):
                    list_sets.append(floodfill(current_cell.pos))
                    
    for s in list_sets:
        total_resource = 0
        for c in s:
            total_resource += c.resource.amount
        
        closest_cell, closest_dist = find_closest_cell_in_list(city_cell.pos, s)
        # Added : keep only sets of resources at sufficient distance
        if closest_dist>2:
            res[closest_cell] = [closest_dist,total_resource]
    
    if res!=[]:
        res = dict(sorted(res.items(), key=lambda item: item[1][0]))
    return res

# Strategy for carts : select randomly the adjacent tile which has the less road value
def move_cart(actions, unit, positions_occupied_next_round):
    neighborhood = adjacent_tiles(unit.pos)
    random.shuffle(neighborhood)
    
    neighbor = neighborhood[0]
    min_road_value = neighbor.road
    
    for n in neighborhood[1:]:
        if n.citytile == None and n.has_resource()== False and n.road<min_road_value:
            neighbor = n
            min_road_value = n.road
    
    next_direction = unit.pos.direction_to(neighbor.pos)
    position_wanted = neighbor.pos.translate(next_direction, 1)
    
    if is_in_map(position_wanted):

        # If no unit want to go there, move. Stay here else.
        if position_wanted not in positions_occupied_next_round:
            positions_occupied_next_round.append(position_wanted)
            action = unit.move(next_direction)
            actions.append(action)
        else:
            neighborhood = adjacent_tiles(unit.pos)
            random.shuffle(neighborhood)
            for a in neighborhood:
                if a.pos not in positions_occupied_next_round:
                    positions_occupied_next_round.append(a.pos)
                    action = unit.move(next_direction)
                    actions.append(action)
                    break



#game_state = None
def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### 
    
    

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    
    # add debug statements like so!
    if game_state.turn == 0:
        print("Agent is running!", file=sys.stderr)
        
    # DEBUG
    #print("###",time_before_nightfall(observation))
        
    
    
    # Shared data
    
    global positions_occupied_next_round
    global initial_city_cell
    global sets_of_resources
    global info_carts
    
    
    
    # Clear the list positions_occupied_next_round
    positions_occupied_next_round = []
    
    
    # Get the cell of the initial city
    cities = list(player.cities.values())
    if game_state.turn == 0:
        initial_city_cell = game_state.map.get_cell_by_pos(cities[0].citytiles[0].pos)
    
    # Update the list of sets of resources
    sets_of_resources = get_sets_of_resources(initial_city_cell)
    
    # Update list of carts
    list_of_carts = get_list_of_carts(player)
    #if game_state.turn == 0:
    info_carts={}
    for i in list_of_carts:
        info_carts[i] = True # True : the cart must go to its target, False : it must return to the city
    
    

    
    resource_tiles = find_resources(game_state)
    
    # Source : https://www.kaggle.com/thalesgaluchi/lux-ai-first-approach
    # ============
    #    CITIES
    # ============
    tiles_in_cities = [ ct for k,city in player.cities.items() for ct in city.citytiles ]
    for k, city in player.cities.items():
        #         if (len(tiles_in_cities)>(len(player.units))):
        for i,city_tile in enumerate(city.citytiles):
            if city_tile.can_act():
                
                N=10
                if (i%N<5):
                    if len(player.units) < player.city_tile_count:
                        action = city_tile.build_worker()
                        #print("<<< Build Worker >>>", action)
                        actions.append(action)
                elif (5<=i%N<8):
                    action = city_tile.research()
                    #print('<<< Research >>> ')
                    actions.append(action)
                
                else:
                    if len(player.units) < player.city_tile_count:
                        action = city_tile.build_cart()
                        #print("<<< Build Cart >>>", action)
                        actions.append(action)
                
                
    
    # ===============================
    #    UNITS (workers and carts) 
    # ===============================
    for i, unit in enumerate(player.units):
        if unit.is_worker() and unit.can_act():
            if player.city_tile_count==0:
                action = unit.build_city()
                actions.append(action)
            else:
                
                closest_city_tile = find_closest_city_tile(unit.pos, player)

                # If there is still space in the cargo, move to the closest resource tile (if possible)
                if unit.get_cargo_space_left()>0:
                    closest_resource_tile = find_closest_resources(unit.pos,player,resource_tiles)
                    if closest_resource_tile != None :
                        next_direction = unit.pos.direction_to(closest_resource_tile.pos)
                        position_wanted = unit.pos.translate(next_direction, 1)
                        if is_in_map(position_wanted):
                            # If no unit want to go there, move. Stay here else.
                            if position_wanted not in positions_occupied_next_round:
                                positions_occupied_next_round.append(position_wanted)
                                action = unit.move(next_direction)
                                actions.append(action)
                            else:
                                neighborhood = adjacent_tiles(unit.pos)
                                random.shuffle(neighborhood)
                                for a in neighborhood:
                                    if a.pos not in positions_occupied_next_round:
                                        next_direction = unit.pos.direction_to(a.pos)
                                        positions_occupied_next_round.append(a.pos)
                                        action = unit.move(next_direction)
                                        actions.append(action)
                                        break


                # If the cargo is full.
                else:

                    city_tiles_fuel = citytiles_sorted_by_fuel_capacity(unit.pos, player)

                    go_to_city_tile = False    
                    for ct in city_tiles_fuel:
                        required_fuel_city = player.cities[ct['tile'].cityid].get_light_upkeep()*10

                        if ct['fuel'] < required_fuel_city:
                            next_direction = unit.pos.direction_to(ct['tile'].pos)

                            position_wanted = unit.pos.translate(next_direction, 1)
                            if is_in_map(position_wanted):
                                # If no unit want to go there, move. Stay here else.
                                if position_wanted not in positions_occupied_next_round:
                                    positions_occupied_next_round.append(position_wanted)
                                    action = unit.move(next_direction)
                                    actions.append(action)
                                else:
                                    neighborhood = adjacent_tiles(unit.pos)
                                    random.shuffle(neighborhood)
                                    for a in neighborhood:
                                        if a.pos not in positions_occupied_next_round:
                                            next_direction = unit.pos.direction_to(a.pos)
                                            positions_occupied_next_round.append(a.pos)
                                            action = unit.move(next_direction)
                                            actions.append(action)
                                            break
                                
                                go_to_city_tile = True
                                break

                    # BUILD
                    if not go_to_city_tile:  
                        tile_to_build = building_tiles(player, unit.pos)
                        
                        if tile_to_build != None:
                            

                            if unit.pos.equals(tile_to_build.pos):
                                
                                if unit.can_build(game_state.map):
                                
                                    action = unit.build_city()
                                    actions.append(action)
                            else:
                                next_direction = direction_to_avoid_citytiles(unit, game_state,tile_to_build.pos)

                                position_wanted = unit.pos.translate(next_direction, 1)
                                if is_in_map(position_wanted):
                                
                                    # If no unit want to go there, move. Stay here else.
                                    if position_wanted not in positions_occupied_next_round:
                                
                                        positions_occupied_next_round.append(position_wanted)
                                        action = unit.move(next_direction)
                                        actions.append(action)
                                    else:
                                
                                        neighborhood = adjacent_tiles(unit.pos)
                                        random.shuffle(neighborhood)
                                        for a in neighborhood:
                                            if a.pos not in positions_occupied_next_round:
                                                next_direction = direction_to_avoid_citytiles(unit, game_state,a.pos)
                                                positions_occupied_next_round.append(a.pos)
                                                action = unit.move(next_direction)
                                                actions.append(action)
                                                break
                                
        if unit.is_cart() and unit.can_act():
            move_cart(actions, unit, positions_occupied_next_round)


    return actions
    