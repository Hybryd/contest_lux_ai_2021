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


### HELPER FUNCTIONS

########
# TIME #
########
def time_before_nightfall(observation):
    """
    Returns the number of steps before nightfall, 0 if it is the night
    """
    step = observation['step']%40
    return max(0,30-step)

def time_before_sunrise(observation):
    """
    Returns the number of steps before sunrise, 0 if it is the day
    """
    step = observation['step']%40
    if time_before_nightfall(observation) == 0:
        return 40-step
    else:
        return 0
    

def time_before_end(observation):
    """
    Returns the number of steps before the end of the simulation
    """
    step = observation['step']%40
    return 360-step


############
# MOVEMENT #
############

def is_in_map(pos):
    """
    Returns True if Position pos belongs to the map
    """
    x = pos.x
    y = pos.y
    w, h = game_state.map.width, game_state.map.height
    return (x<w)&(y<w)&(x>=0)&(y>=0)

# Redefine Position.direction_to to avoid citytiles
def direction_to_avoid_citytiles(unit, game_state, target_pos):
    """
    Returns closest position to target_pos from this position, if it is not a citytile (except target_pos)
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
    while i<4 and (is_in_map(unit.pos.translate(check_dirs[i], 1))) and (unit.pos.translate(check_dirs[i], 1) != target_pos and game_state.map.get_cell_by_pos(unit.pos.translate(check_dirs[i], 1)).citytile!=None):
        i+=1

    if i<4:
        direction = check_dirs[i]
        #print("====DEBUG==== direction",direction)

        newpos = unit.pos.translate(direction, 1)
        #print("====DEBUG==== newpos",newpos)
        #if newpos == target_pos or game_state.map.get_cell_by_pos(newpos).citytile==None:
        closest_dist = unit.pos.translate(check_dirs[i], 1).distance_to(target_pos)
        #print("====DEBUG==== closest_dist",closest_dist)

        #closest_dir = DIRECTIONS.CENTER
        closest_dir = check_dirs[i]
        #print("====DEBUG==== closest_dir",closest_dir)
        for direction in check_dirs:
            newpos = unit.pos.translate(direction, 1)
            if is_in_map(newpos):
                #print("====DEBUG==== newpos",newpos)
                #print("====DEBUG==== game_state.map.get_cell_by_pos(newpos).citytile",game_state.map.get_cell_by_pos(newpos).citytile)
                if game_state.map.get_cell_by_pos(newpos) != None:
                    if newpos == target_pos or game_state.map.get_cell_by_pos(newpos).citytile==None:
                        #print("====DEBUG==== dans le if")
                        dist = target_pos.distance_to(newpos)
                        #print("====DEBUG==== dist",dist)
                        if dist < closest_dist:
                            closest_dir = direction
                            closest_dist = dist
                            #print("====DEBUG==== MAJ. closest_dir",closest_dir,"closest_dist",closest_dist)

            #print("====DEBUG==== closest_dir",closest_dir)


    return closest_dir





##################
# CELLS RESEARCH #
##################

def adjacent_tiles(pos):
    """
    Get adjacent tiles given a tile
    """
    x1,y1 = pos.x, pos.y
    w, h = game_state.map.width, game_state.map.height
    adjacent_tiles_pos = [(x1-1,y1),(x1+1,y1),(x1,y1+1),(x1,y1-1)]
    return [ game_state.map.get_cell(x,y) for (x,y) in adjacent_tiles_pos if (x<w)&(y<w)&(x>=0)&(y>=0) ]




def find_empty(game_state):
    """
    Returns the list of empty Cell
    """
    empty_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if not cell.has_resource() and cell.citytile == None:
                empty_tiles.append(cell)
    return empty_tiles


def find_closest_empty(pos, player, empty_tiles):
    """
    Returns the closest empty Cell that a worker can build on.
    
    """
    closest_dist = math.inf
    closest_empty_tile = None
    
    for empty_tile in empty_tiles:
        dist = empty_tile.pos.distance_to(pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_empty_tile = empty_tile
            
    return closest_empty_tile



def find_closest_empty_tile(pos, player):
    """
    Returns the closest empty Cell
    """
    closest_empty_tile = None

    closest_dist = math.inf
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile

def find_closest_city_tile(pos, player):
    """
    Returns the closest city Cell
    """
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile

def find_closest_city_tile_in_city(pos, player, cit):
    """
    Returns the closest city Cell among the given City
    """
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        for k, city in player.cities.items():
            if city == cit:
                for city_tile in city.citytiles:
                    dist = city_tile.pos.distance_to(pos)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_city_tile = city_tile
    return closest_city_tile

def find_closest_cell_in_list(pos, list_cells):
    """
    Returns the closest Cell and corresponding distance, among the given list of Cell
    """
    closest_cell = None
    closest_dist = math.inf
    if len(list_cells) > 0:
        for c in list_cells:
            dist = c.pos.distance_to(pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_cell = c
    return closest_cell, closest_dist


def citytiles_sorted_by_fuel_capacity(pos, player):
    """
    Returns the list of the closest citytiles belonging to different cities, sorted by amount of fuel available in the corresponding cities
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

def floodfill(pos):
    """
    Applies the floodfill algorithm to return the list of Cell connected to the given Position and having the same Resource type
    """
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

def get_clusters_of_resources(city_cell):
    """
    Returns a dict {closest_cell : [closest_dist, total_ressource]}
        closest_cell    : the closest Cell belonging to a cluster of same resource
        closest_dist    : the distance to closest_cell
        total_ressource : the total amount of resource the cluster contains
        
    """
    res={}
    list_clusters = []
    for x in range(game_state.map.width):
        for y in range(game_state.map.height):
            current_cell = game_state.map.get_cell(x,y)
            if current_cell.has_resource():
                if current_cell not in (item for sublist in list_clusters for item in sublist):
                    list_clusters.append(floodfill(current_cell.pos))
                    
    for s in list_clusters:
        total_resource = 0
        for c in s:
            total_resource += c.resource.amount
        
        closest_cell, closest_dist = find_closest_cell_in_list(city_cell.pos, s)
        
        #  Keep only sets of resources at sufficient distance
        if closest_dist>2:
            res[closest_cell] = [closest_dist,total_resource]
    
    if res!=[]:
        res = dict(sorted(res.items(), key=lambda item: item[1][0]))
    return res

#########
# UNITS #
#########

def get_list_of_carts(player):
    """
    Returns the list of cart units
    """
    res = []
    for u in player.units:
        if u.is_cart():
            res.append(u)
    return res


def get_list_of_workers(player):
    """
    Returns the list of cart units
    """
    res = []
    for u in player.units:
        if u.is_worker():
            res.append(u)
    return res


#############
# RESOURCES #
#############
def find_resources(game_state):
    """
    Returns the list of resource Cell
    """
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles


def find_closest_resources(pos, player, resource_tiles):
    """
    Returns the closest resource Cell that a worker can mine.
    Priority order : uranium, coal, wood
    """
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



###########
# WORKERS #
###########

def building_tiles(player, pos): # TODO: change to pos, player)
    """
    Return the chosen Cell where the worker is going to build a city
    """
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

def move_worker(unit, target_cell, positions_occupied_next_round, actions, info_map):
    #print('====DEBUG== In move_worker. unit.pos', unit.pos)
    next_direction = unit.pos.direction_to(target_cell.pos)
    position_wanted = unit.pos.translate(next_direction, 1)
    #print('====DEBUG== position_wanted',position_wanted)
    
    if is_in_map(position_wanted):
        #print('====DEBUG== is_in_map(position_wanted)',is_in_map(position_wanted))
        # If no unit want to go there, move. Stay here else.
        if position_wanted not in positions_occupied_next_round:
            positions_occupied_next_round.append(position_wanted)
            action = unit.move(next_direction)
            actions.append(action)
            info_map[position_wanted.y][position_wanted.x]+=1
            #print('====DEBUG== position_wanted not in positions_occupied_next_round')
        else:
            # If another unit will go to the position_wanted in next step, choose randomly another Position around him
            neighborhood = adjacent_tiles(unit.pos)
            random.shuffle(neighborhood)
            for a in neighborhood:
                if a.pos not in positions_occupied_next_round:
                    next_direction = unit.pos.direction_to(a.pos)
                    positions_occupied_next_round.append(a.pos)
                    action = unit.move(next_direction)
                    actions.append(action)
                    info_map[a.pos.y][a.pos.x]+=1
                    #print('====DEBUG== position reserved:', a.pos)
                    break

def move_worker_avoid_city_tiles(unit, target_cell, positions_occupied_next_round, actions, info_map):
    #print('====DEBUG== In move_worker_avoid_city_tiles. unit.pos', unit.pos)
    #next_direction = unit.pos.direction_to(target_cell.pos)
    next_direction = direction_to_avoid_citytiles(unit, game_state, target_cell.pos)
    position_wanted = unit.pos.translate(next_direction, 1)
    #print('====DEBUG== position_wanted',position_wanted)
    
    if is_in_map(position_wanted):
        #print('====DEBUG== is_in_map(position_wanted)',is_in_map(position_wanted))
        # If no unit want to go there, move. Stay here else.
        if position_wanted not in positions_occupied_next_round:
            positions_occupied_next_round.append(position_wanted)
            action = unit.move(next_direction)
            actions.append(action)
            info_map[position_wanted.y][position_wanted.x]+=1
            #print('====DEBUG== position_wanted not in positions_occupied_next_round')
        else:
            # If another unit will go to the position_wanted in next step, choose randomly another Position around him
            neighborhood = adjacent_tiles(unit.pos)
            random.shuffle(neighborhood)
            for a in neighborhood:
                if a.pos not in positions_occupied_next_round:
                    next_direction = direction_to_avoid_citytiles(unit, game_state, a.pos)
                    positions_occupied_next_round.append(a.pos)
                    action = unit.move(next_direction)
                    actions.append(action)
                    info_map[a.pos.y][a.pos.x]+=1
                    #print('====DEBUG== position reserved:', a.pos)
                    break

#########
# CARTS #
#########
def move_cart(unit, positions_occupied_next_round, actions, info_map):
    """
    Strategy: build roads where units have been the less
    """
    neighborhood = adjacent_tiles(unit.pos)
    neighbor = neighborhood[0]
    min_info_map_value = info_map[neighbor.pos.y][neighbor.pos.x]
    
    for n in neighborhood[1:]:
        if n.citytile == None and n.has_resource()== False and info_map[n.pos.y][n.pos.x]<min_info_map_value:
            neighbor = n
            min_info_map_value = info_map[n.pos.y][n.pos.x]
    
    move_worker(unit, neighbor, positions_occupied_next_round, actions, info_map)

    
##########
# CITIES #
##########
def cities_can_survive(unit, player, observation):
    res = True
    city_tiles_fuel = citytiles_sorted_by_fuel_capacity(unit.pos, player)
    for ct in city_tiles_fuel:
        required_fuel_city = player.cities[ct['tile'].cityid].get_light_upkeep()*time_before_sunrise(observation)
        res &= ct['fuel'] < required_fuel_city
    return res
    
    
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
    global clusters_of_resources
    global info_carts
    global info_map
    
    
    
    # Clear the list positions_occupied_next_round
    positions_occupied_next_round = []
    
    
    # Get the cell of the initial city
    cities = list(player.cities.values())
    if game_state.turn == 0:
        initial_city_cell = game_state.map.get_cell_by_pos(cities[0].citytiles[0].pos)
    
    # Update the list of sets of resources
    clusters_of_resources = get_clusters_of_resources(initial_city_cell)
    
    # Update list of carts
    list_of_carts = get_list_of_carts(player)
    #if game_state.turn == 0:
    info_carts={}
    for i in list_of_carts:
        info_carts[i] = True # True : the cart must go to its target, False : it must return to the city
    
    # info_map is a copy of the map. Each element contains an integer counting the number of times a worker has been on.
    # Useful to pave a road
    if game_state.turn == 0:
        # Initialisation of info_map
        info_map = [None] * height
        for y in range(height):
            info_map[y] = [None] * width
            for x in range(width):
                info_map[y][x] = 0
    
        

    
    resource_tiles = find_resources(game_state)
    
    
    ##########
    # CITIES #
    ##########
    # Cities roles proportions
    p_worker = 0.5
    p_research = 0.3
    p_cart = 0.2
    
    # Compute roles of cities
    number_cities = player.city_tile_count
    index_tmp=0
    cities_indices = [*range(number_cities)]
    cities_worker = cities_indices[index_tmp:index_tmp+int(p_worker*number_cities)]
    index_tmp += int(p_worker*number_cities)
    cities_research = cities_indices[index_tmp:index_tmp+int(p_research*number_cities)]
    index_tmp += int(p_research*number_cities)
    cities_cart = cities_indices[index_tmp:]
    
    
    
    tiles_in_cities = [ ct for k,city in player.cities.items() for ct in city.citytiles ]
    for k, city in player.cities.items():
        for i,city_tile in enumerate(city.citytiles):
            if city_tile.can_act():
                if i in cities_worker:
                    closest_resource = find_closest_resources(city_tile.pos, player, resource_tiles)
                    if closest_resource != None:
                        closest_resource_dist = city_tile.pos.distance_to(closest_resource.pos)
                        if time_before_nightfall(observation) > closest_resource_dist and len(player.units) < player.city_tile_count:
                            action = city_tile.build_worker()
                            #print("<<< Build Worker >>>", action)
                            actions.append(action)
                        else :
                            action = city_tile.research()
                            #print('<<< Research >>> ')
                            actions.append(action)
                    else :
                        action = city_tile.research()
                        #print('<<< Research >>> ')
                        actions.append(action)
                elif i in cities_research:
                    if player.research_points < 200:
                        action = city_tile.research()
                        #print('<<< Research >>> ')
                        actions.append(action)
                    else :
                        if (i%2==0):
                            action = city_tile.build_cart()
                            #print("<<< Build Cart >>>", action)
                            actions.append(action)
                        else:
                            action = city_tile.build_worker()
                            #print("<<< Build Worker >>>", action)
                            actions.append(action)
                        
                else:
                    closest_resource = find_closest_resources(city_tile.pos, player, resource_tiles)
                    if closest_resource != None:
                        closest_resource_dist = city_tile.pos.distance_to(closest_resource.pos)
                        if time_before_nightfall(observation) > closest_resource_dist and len(player.units) < player.city_tile_count:
                            action = city_tile.build_cart()
                            #print("<<< Build Cart >>>", action)
                            actions.append(action)
                        else :
                            action = city_tile.research()
                            #print('<<< Research >>> ')
                            actions.append(action)
                    else :
                        action = city_tile.research()
                        #print('<<< Research >>> ')
                        actions.append(action)

                
    #########
    # UNITS #
    #########
    
    for i, unit in enumerate(player.units):
        
        ###########
        # WORKERS #
        ###########
        if unit.is_worker() and unit.can_act():
            if player.city_tile_count==0:
                #print('==DEBUG== EMERGENCY. Worker build a city')
                empty_tiles = find_empty(game_state)
                closest_empty_cell = find_closest_empty(unit.pos, player, empty_tiles)
                
                if unit.pos.equals(closest_empty_cell.pos):
                    #print('==DEBUG== Worker on tile_to_build')
                    if unit.can_build(game_state.map):
                        #print('==DEBUG== Worker can build')
                        action = unit.build_city()
                        actions.append(action)
                else:
                    #print('==DEBUG== Worker move')
                    move_worker(unit, closest_empty_cell, positions_occupied_next_round, actions, info_map)
                #action = unit.build_city()
                #actions.append(action)
                
            else:
                '''
                print("==== DEBUG ==== time_before_end(observation)",time_before_end(observation))
                print("==== DEBUG ==== cities_can_survive(unit, player, observation)",cities_can_survive(unit, player, observation))
                # If end is close and all the cities can survive the night, workers build a citytile
                if time_before_end(observation)<10 and cities_can_survive(unit, player, observation):
                    print("==== DEBUG ==== END IS CLOSE!")
                    tile_to_build = building_tiles(player, unit.pos)
                    if tile_to_build != None:
                        if unit.pos.equals(tile_to_build.pos):
                            if unit.can_build(game_state.map):
                                action = unit.build_city()
                                actions.append(action)
                                #print("==== DEBUG ==== BUILD NEW CITYTILE")
                        else:
                            move_worker(unit, tile_to_build, positions_occupied_next_round, actions, info_map)
                
                else:
                '''
                if True:

                    closest_city_tile = find_closest_city_tile(unit.pos, player)

                    # If there is still space in the cargo, move to the closest resource tile (if possible)
                    if unit.get_cargo_space_left()>0:
                        closest_resource_tile = find_closest_resources(unit.pos,player,resource_tiles)
                        if closest_resource_tile != None:
                            move_worker(unit, closest_resource_tile, positions_occupied_next_round, actions, info_map)



                    # If the cargo is full.
                    else:
                        
                        city_tiles_fuel = citytiles_sorted_by_fuel_capacity(unit.pos, player)

                        # We are winning if we have more than 3 times more citytiles than the opponent
                        we_are_winning = opponent.city_tile_count*3<player.city_tile_count
                        
                        go_to_city_tile = False    
                        for ct in city_tiles_fuel:
                            required_fuel_city = player.cities[ct['tile'].cityid].get_light_upkeep()*10

                            if ct['fuel'] < required_fuel_city or we_are_winning:
                                #print("==== DEBUG ==== GOTOCITY")
                                move_worker(unit, ct['tile'], positions_occupied_next_round, actions, info_map)
                                go_to_city_tile = True



                        # BUILD
                        if not go_to_city_tile:
                            #print("==== DEBUG ==== GO BUILD")
                            tile_to_build = building_tiles(player, unit.pos)
                            #print("==== DEBUG ==== tile_to_build",tile_to_build.pos)
                            #print('==DEBUG== Worker pos',unit.pos)
                            if tile_to_build != None:
                                #print('==DEBUG== tile_to_build.pos',tile_to_build.pos)

                                if unit.pos.equals(tile_to_build.pos):
                                    #print('==DEBUG== Worker on tile_to_build')
                                    if unit.can_build(game_state.map):
                                        #print('==DEBUG== Worker can build')
                                        action = unit.build_city()
                                        actions.append(action)
                                else:
                                    #print('==DEBUG== Worker move')
                                    move_worker_avoid_city_tiles(unit, tile_to_build, positions_occupied_next_round, actions, info_map)

        
        #########
        # CARTS #
        #########
        if unit.is_cart() and unit.can_act():
            move_cart(unit, positions_occupied_next_round, actions, info_map)
    
    return actions