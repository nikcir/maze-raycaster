import pygame
import math
import numpy as np
import random

# Initialiser pygame
pygame.init()

class Colors:
    """Sentraliserer fargedefinisjoner for bedre organisering og gjenbruk."""
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)  
    SKY_BLUE = (135, 206, 235)
    LIME = (50, 255, 50)  
    GROUND_GREEN = (34, 139, 34)
    GROUND_BROWN = (189, 119, 69)
    MENU_BG = (40, 40, 60, 200)  
    MENU_HIGHLIGHT = (100, 100, 255) 

class PlayerReflection:
    """
    Lagrer data om spillerrefleksjoner for senere tegning.
    Brukes for å håndtere korrekt visning av spillerrefleksjoner i speil.
    """
    def __init__(self, screen_x, depth, width, mirror_level=1):
        self.screen_x = screen_x         # X-posisjon på skjermen
        self.depth = depth               # Avstand fra betrakteren
        self.width = width               # Bredden på strålen ved dette punktet
        self.mirror_level = mirror_level # Hvor mange speil dypt (for intensitet)
 
class Entity:
    """
    Basisklasse for alle enheter i spillet.
    Håndterer grunnleggende posisjonering, bevegelse og kollisjonsdeteksjon.
    """
    def __init__(self, maze, raycaster, speed=3, entity_type="entity"):
        self.maze = maze
        self.raycaster = raycaster
        self.speed = speed
        self.entity_type = entity_type
        self.spawn()
   
    def spawn(self):
        """Plasserer enheten tilfeldig i en tom celle i labyrinten."""
        while True:
            row = random.randint(1, len(self.maze) - 2)  # Unngå yttervegger
            col = random.randint(1, len(self.maze[0]) - 2)
            if self.maze[row][col] == 0:
                self.x = (col + 0.5) * self.raycaster.cell_size
                self.y = (row + 0.5) * self.raycaster.cell_size
                return
   
    def move(self, dx, dy):
        """
        Håndterer bevegelse med kollisjonsdeteksjon mot vegger.
        Sjekker kollisjon separat for x- og y-aksen for å tillate gliding bevegelse langs vegger.
        """
        new_x = self.x + dx
        new_y = self.y + dy
       
        # Sjekk x-akse kollisjon
        col, row = int(new_x // self.raycaster.cell_size), int(self.y // self.raycaster.cell_size)
        if 0 <= row < len(self.maze) and 0 <= col < len(self.maze[0]) and self.maze[row][col] == 0:
            self.x = new_x
       
        # Sjekk y-akse kollisjon
        col, row = int(self.x // self.raycaster.cell_size), int(new_y // self.raycaster.cell_size)
        if 0 <= row < len(self.maze) and 0 <= col < len(self.maze[0]) and self.maze[row][col] == 0:
            self.y = new_y
 
class Player(Entity):
    """
    Spillerkontrollert entitet. Håndterer tastaturinput for bevegelse og rotasjon.
    Arver fra Entity-klassen.
    """
    def __init__(self, maze, raycaster, rotation_speed=3):
        super().__init__(maze, raycaster, speed=3, entity_type="player")
        self.rotation_speed = rotation_speed
        self.z_rotation = 0
        self.z = 0
        self.angle = 0
   
    def move(self):
        """
        Håndterer spillerens bevegelse basert på tastaturinput.
        Implementerer både WASD og piltaster for bevegelse, og IJKL for rotasjon.
        """
        keys = pygame.key.get_pressed()
        sin_a = math.sin(math.radians(self.angle))
        cos_a = math.cos(math.radians(self.angle))
 
        if keys[pygame.K_LSHIFT]:
            self.speed = 8
            self.rotation_speed = 12
        else:
            self.speed = 3
            self.rotation_speed = 5 
 
        # Rotasjonskontroller med IJKL
        if keys[pygame.K_j]:  # Venstre rotasjon
            self.angle -= self.rotation_speed
        if keys[pygame.K_l]:  # Høyre rotasjon
            self.angle += self.rotation_speed
        if keys[pygame.K_i]:  # Opp rotasjon
            self.z_rotation -= self.rotation_speed*5
        if keys[pygame.K_k]:  # Ned rotasjon
            self.z_rotation += self.rotation_speed*5
       
        dx, dy = 0, 0
        # Bevegelseskontroller med piltaster eller WASD
        if keys[pygame.K_w] or keys[pygame.K_UP]:  # Framover bevegelse
            dx += self.speed * cos_a
            dy += self.speed * sin_a
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  # Bakover bevegelse
            dx -= self.speed * cos_a
            dy -= self.speed * sin_a
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  # Venstre bevegelse
            dx += self.speed * sin_a
            dy -= self.speed * cos_a
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  # Høyre bevegelse
            dx -= self.speed * sin_a
            dy += self.speed * cos_a
       
        super().move(dx, dy)
 
class Monster(Entity):
    """
    Monster som følger spilleren.
    Bruker A* pathfinding for å følge spilleren.
    """
    def __init__(self, maze, raycaster):
        super().__init__(maze, raycaster, speed=1.5, entity_type="monster")
        self.detection_range = 5 * raycaster.cell_size  # Deteksjonsrekkevidde i piksler
        self.path = []
        self.path_update_timer = 0
        self.path_update_interval = 30  # Oppdater banen hvert 30. frame
        self.height = 30  # Monsterhøyde for rendering
        self.width = 30   # Monsterbredde for rendering
        self.collision_radius = raycaster.cell_size * 0.05 #Monster hitbox

        # Tilfeldig mørk farge
        r = random.randint(50, 70)   
        g = random.randint(25, 50)  
        b = random.randint(0, 40)    
        self.color = (r, g, b)
   
    def update(self, player, other_monsters):
        """
        Oppdaterer monsterets tilstand og posisjon.
        Oppdaterer banen til spilleren hvis innenfor deteksjonsrekkevidden.
        Håndterer kollisjon med andre monstre.
        """
        self.path_update_timer += 1
       
        # Beregn avstand til spiller
        distance_to_player = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
       
        # Oppdater banen hvis innenfor deteksjonsrekkevidde og tid for oppdatering
        if distance_to_player < self.detection_range and self.path_update_timer >= self.path_update_interval:
            self.find_path_to_player(player)
            self.path_update_timer = 0
       
        # Beveg langs banen hvis den eksisterer
        if self.path:
            next_point = self.path[0]
            target_x, target_y = next_point
           
            # Beregn retningsvektor
            dx = target_x - self.x
            dy = target_y - self.y
           
            # Normaliser retningsvektor
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                dx = dx / distance * self.speed
                dy = dy / distance * self.speed
           
            # Sjekk for kollisjoner med andre monstre før bevegelse
            new_x = self.x + dx
            new_y = self.y + dy
           
            # Sjekk for monster-monster-kollisjoner
            monster_collision = False
            for other in other_monsters:
                if other != self:  # Ikke sjekk kollisjon med seg selv
                    dist = math.sqrt((new_x - other.x)**2 + (new_y - other.y)**2)
                    if dist < (self.collision_radius + other.collision_radius):
                        monster_collision = True
                        
                        # Ved kollisjon, vent på stedet med sjanse for å beregne banen på nytt
                        if random.random() < 0.3:  # 30% sjanse for å beregne banen på nytt
                            self.path_update_timer = self.path_update_interval
                        break
           
            # Beveg bare hvis ingen monster-kollisjon
            if not monster_collision:
                # Beveg monsteret med veggkollisjonsdeteksjon
                super().move(dx, dy)
           
            # Sjekk om veipunktet er nådd
            if distance < self.speed * 2:
                self.path.pop(0)
   
    def find_path_to_player(self, player):
        """
        A* pathfinding algoritme for å finne optimal rute til spilleren.
        Lager en liste med veipunkter som monsteret følger.
        lærte om det her: https://en.wikipedia.org/wiki/A*_search_algorithm#Further_reading
        """
        start = (int(self.y // self.raycaster.cell_size), int(self.x // self.raycaster.cell_size))
        goal = (int(player.y // self.raycaster.cell_size), int(player.x // self.raycaster.cell_size))
       
        # Ikke forsøk å finne vei hvis vi er i samme celle
        if start == goal:
            self.path = []
            return
       
        # A* implementasjon
        open_set = [(self.heuristic(start, goal), start)]
        came_from = {}
        g_score = {start: 0}
       
        while open_set:
            # Finn indeksen til noden med lavest f_score
            min_idx = 0
            for i in range(1, len(open_set)):
                if open_set[i][0] < open_set[min_idx][0]:
                    min_idx = i
            
            # Hent gjeldende node og fjern den
            _, current = open_set.pop(min_idx)
           
            if current == goal:
                # Rekonstruer stien
                path = []
                while current in came_from:
                    # Konverter rutenettkoordinater til verdenskoordinater
                    row, col = current
                    path.append(((col + 0.5) * self.raycaster.cell_size, (row + 0.5) * self.raycaster.cell_size))
                    current = came_from[current]
                path.reverse()
                self.path = path
                return
           
            # Sjekk naboer
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                neighbor = (current[0] + dr, current[1] + dc)
                row, col = neighbor
               
                # Sjekk om gyldig og gangbar
                if (0 <= row < len(self.maze) and 0 <= col < len(self.maze[0]) and
                    self.maze[row][col] == 0):
                   
                    tentative_g = g_score[current] + 1
                   
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + self.heuristic(neighbor, goal)
                        if (f_score, neighbor) not in open_set:
                            open_set.append((f_score, neighbor))
       
        # Ingen vei funnet
        self.path = []
   
    def heuristic(self, a, b):
        """
        Manhattan avstand heuristikk for A* pathfinding algoritme.
        Estimerer avstand mellom to punkter i rutenettet.
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
   
class Raycaster:
    """
    Hovedklasse for raycasting-algoritmen.
    Håndterer raycasting, rendering av 3D, og speilrefleksjoner.
    """
    def __init__(self, maze, cell_size, fov, num_rays, max_depth):
        self.maze = maze
        self.cell_size = cell_size
        self.fov = fov
        self.num_rays = num_rays
        self.max_depth = max_depth
        self.ray_angle_step = fov / num_rays
        self.max_recursion_depth = 10  # Begrens rekursjonsdybden for å unngå ekstrem lag og krasj
        self.show_rays = True  # Boolean for å veksle strålesynlighet
        self.mirror_alpha = 20
        
        # Lagre spillerrefleksjoner for å ha sist i tegnerekkefølgen
        self.player_reflections = []
        
        # Antialiasing innstillinger
        self.antialiasing_levels = [
            {"increment": 5, "depth_check": 5},    # Av
            {"increment": 5, "depth_check": 0.5},  # Lav
            {"increment": 3, "depth_check": 0.3},  # Middels
            {"increment": 2, "depth_check": 0.1},  # Høy
            {"increment": 2, "depth_check": 0.01}  # Ultra
        ]
    
    def cast_ray(self, px, py, angle, settings, dep=0):
        """
        Standard raycasting for vegger.
        Kaster en stråle fra gitt posisjon og vinkel, og returnerer treffpunkt og informasjon.
        """
        aa_level = min(settings["antialiasing"][0], len(self.antialiasing_levels) - 1)
        aa_settings = self.antialiasing_levels[aa_level]
    
        ray_x, ray_y = px, py
        old_col, old_row = int(ray_x // self.cell_size), int(ray_y // self.cell_size)
        sin_a = math.sin(math.radians(angle))
        cos_a = math.cos(math.radians(angle))
        increment = aa_settings["increment"]
        depth_check = aa_settings["depth_check"]
        cell = 0
        side = None
        
        # Hovedløkke for raycasting
        for depth in np.arange(dep, settings["render_distance"][0], increment):
            ray_x += cos_a * increment
            ray_y += sin_a * increment
            col, row = int(ray_x // self.cell_size), int(ray_y // self.cell_size)
            
            # Sjekk for veggkollisjon
            if 0 <= row < len(self.maze) and 0 <= col < len(self.maze[0]) and self.maze[row][col] >= 1:
                # Bestem hvilken side vi traff
                if old_row-row == -1:
                    side = "BOTTOM"
                elif old_col-col == 1:
                    side = "LEFT"
                elif old_col-col == -1:
                    side = "RIGHT"
                elif old_row-row == 1:
                    side = "TOP"
        
                cell = self.maze[row][col]

                # Finjuster treffpunktet for økt presisjon med "antialiasing"
                for i in range(int(increment/depth_check)):
                    ray_x -= cos_a * depth_check
                    ray_y -= sin_a * depth_check
                    col, row = int(ray_x // self.cell_size), int(ray_y // self.cell_size)
                    if not(0 <= row < len(self.maze) and 0 <= col < len(self.maze[0]) and self.maze[row][col] >= 1):
                        depth -= (i) * depth_check
                        break
        
                return ray_x, ray_y, depth, cell, side
                
            old_col, old_row = col, row
        
        # Ingen veggtreff funnet
        return ray_x, ray_y, self.max_depth, cell, side

    def check_player_reflection(self, px, py, angle, player_pos, settings):
        """
        Spesialisert strålekast for å sjekke spillerrefleksjoner.
        Returnerer dybde til spilleren hvis funnet, ellers None.
        """
        # Hopp over hvis kilde og mål er det samme (unngå selvdeteksjon)
        if abs(px - player_pos[0]) < 1 and abs(py - player_pos[1]) < 1:
            return None
            
        aa_level = min(settings["antialiasing"][0], len(self.antialiasing_levels) - 1)
        aa_settings = self.antialiasing_levels[aa_level]
        
        player_x, player_y = player_pos
        player_radius = 4  # Hitbox for spiller
        
        # Mindre økninger for mer presis deteksjon
        increment = min(2, aa_settings["increment"])
        
        ray_x, ray_y = px, py
        sin_a = math.sin(math.radians(angle))
        cos_a = math.cos(math.radians(angle))
        
        # Sjekk begrenset avstand for ytelse
        max_check_distance = min(settings["render_distance"][0], 500)
        
        for depth in np.arange(0, max_check_distance, increment):
            ray_x += cos_a * increment
            ray_y += sin_a * increment
            
            # Sjekk om vi traff en vegg først (som ville blokkere spillervisning)
            col, row = int(ray_x // self.cell_size), int(ray_y // self.cell_size)
            if (0 <= row < len(self.maze) and 0 <= col < len(self.maze[0]) and 
                self.maze[row][col] >= 1):
                # Traff vegg først, ingen spillerrefleksjon
                return None
                
            # Sjekk for spillerkollisjon
            dist_to_player = math.sqrt((ray_x - player_x)**2 + (ray_y - player_y)**2)
            if dist_to_player <= player_radius:
                # Fant spiller og returner refleksjonsinfo
                return depth
        
        # Ingen spiller funnet innen rekkevidde
        return None
 
    def draw_minimap(self, screen, player):
        """
        Tegner minimap med vegger og spilleren.
        """
        for row_idx, row in enumerate(self.maze):
            for col_idx, cell in enumerate(row):
                if cell == 1:
                    color = Colors.WHITE
                elif cell == 2:
                    color = Colors.SKY_BLUE
                elif cell == 3:  
                    color = Colors.RED
                else:
                    color = Colors.BLACK
                pygame.draw.rect(
                    screen,
                    color,
                    pygame.Rect(
                        col_idx * self.cell_size,
                        row_idx * self.cell_size,
                        self.cell_size,
                        self.cell_size,
                    ),
                )
        # Tegn spilleren 
        pygame.draw.circle(screen, Colors.BLUE, (int(player.x), int(player.y)), 5)
 
    def draw_recursive_ray(self, screen, x1, y1, x2, y2, cell, side, settings, current_depth=0, is_reflection=False):
        """
        Rekursiv funksjon for å tegne reflekterte stråler og håndtere flere refleksjoner.
        Håndterer speilrefleksjoner og dybdebegrensning.
        """
        # Sjekk rekursjonsdybde
        if current_depth >= self.max_recursion_depth:
            return
            
        # Velg strålefarger - lime for refleksjoner, rød for primære stråler
        ray_color = Colors.LIME if is_reflection else Colors.RED
        
        # Tegn gjeldende strålesegment med rett farge
        pygame.draw.line(
            screen,
            ray_color,
            (x1, y1),
            (x2, y2),
            1,
        )
        
        # Håndter refleksjon hvis strålen traff et speil
        if cell == 2:
            r_x, r_y = self.reflect_vector(x2-x1, y2-y1, side)
            _, adjusted_ray_angle = self.angle_of_vector(r_x, r_y)

            # Bruk standard raycasting for map
            new_ray_x, new_ray_y, _, cell, side = self.cast_ray(x2, y2, adjusted_ray_angle, settings)
            
            # Rekursivt kall med is_reflection=True for å indikere at dette er en reflektert stråle
            self.draw_recursive_ray(screen, x2, y2, new_ray_x, new_ray_y, 
                                    cell, side, settings, current_depth + 1, True)

    def draw_rays(self, screen, player, settings):
        """
        Tegner raycasting stråler for visualisering i minimap.
        Håndterer både primære og reflekterte stråler.
        """
        if not self.show_rays:  # Hopp over tegning av stråler hvis slått av
            return
            
        for i in range(settings["num_rays"][0]):
            ray_angle = player.angle - settings["fov"][0] / 2 + i * (settings["fov"][0]/settings["num_rays"][0])
            # Bruk standard raycasting for map
            ray_x, ray_y, depth, cell, side = self.cast_ray(player.x, player.y, ray_angle, settings)

            # Start rekursiv stråletegning
            self.draw_recursive_ray(screen, player.x, player.y, ray_x, ray_y, 
                                     cell, side, settings)

    def draw_recursive_wall(self, screen, screen_height, player, settings, depth, x1, y1, x2, y2, 
                               cell, side, levels, screen_x, ray_width, alpha):
        """
        Rekursiv funksjon for å tegne vegger og samle spillerrefleksjonsdata.
        Håndterer speilrefleksjoner og dybdebegrensning.
        """
        # Begrens rekursjonsdybde
        if levels > self.max_recursion_depth:
            return
            
        # Håndter speilrefleksjoner
        if cell == 2:

            # Beregn speilhøyde
            draw_depth = max(0.1, depth)
            wall_height = screen_height / (draw_depth / 25 + 0.1) / (settings["fov"][0]/90)
            wall_height = max(1, min(int(wall_height), 10000))
            
            # Tegn speil
            color_mirror = (255, 255, 255, min(255, alpha*levels))
            rect_surface = pygame.Surface((ray_width, wall_height), pygame.SRCALPHA)
            rect_surface.fill(color_mirror)
            screen.blit(rect_surface, (screen_x, screen_height / 2 - wall_height / 2 - player.z_rotation))

            # Beregn refleksjonsvektor
            r_x, r_y = self.reflect_vector(x2-x1, y2-y1, side)
            _, adjusted_ray_angle = self.angle_of_vector(r_x, r_y)
            
            # Sjekk for spillerrefleksjon
            player_depth = self.check_player_reflection(
                x2, y2, adjusted_ray_angle, (player.x, player.y), settings)
            
            if player_depth is not None:
                # Lagre spillerrefleksjonsdata for senere tegning
                reflection = PlayerReflection(
                    screen_x,             # Skjerm X-posisjon 
                    player_depth + depth, # Total dybde (avstand)
                    ray_width,            # Bredde på denne strålen
                    levels                # Speilnivå (for intensitet)
                )
                self.player_reflections.append(reflection)
            
            # Fortsett veggtegning med reflektert stråle
            new_ray_x, new_ray_y, second_depth, new_cell, new_side = self.cast_ray(
                x2, y2, adjusted_ray_angle, settings)
            
            # Fortsett rekursjon for vegger i refleksjon
            new_depth = depth + second_depth
            self.draw_recursive_wall(
                screen, screen_height, player, settings, new_depth, 
                x2, y2, new_ray_x, new_ray_y, new_cell, new_side, 
                levels+1, screen_x, ray_width, alpha)
            
        # Standard vegg tegning
        else:
            # Beregn vegghøyde
            safe_depth = max(0.1, depth)
            wall_height = screen_height / (safe_depth / 25 + 0.1) / (settings["fov"][0]/90)
            wall_height = max(1, min(int(wall_height), 10000))
            
            # Velg farge basert på objekttype
            if cell == 3:
                color = Colors.RED
            else:
                color = (255 / (1 + max(0, depth) * 0.001),) * 3

            # Tegn vegg/objekt
            pygame.draw.rect(
                screen,
                color,
                (screen_x, screen_height / 2 - wall_height / 2 - player.z_rotation, 
                ray_width, wall_height),
            )

    def draw_3d_scene(self, screen, player, settings, screen_width, screen_height):
        """
        To trinn for tegningen av 3D senen:
        1. Cast rays og tegne vegger mens refleksjonsdata samles
        2. Tegne spillerrefleksjoner på toppen i en separat gjennomgang
        """
        # Tøm refleksjonslisten for denne framen
        self.player_reflections = []
        
        # Tegn bakgrunn
        pygame.draw.rect(screen, Colors.SKY_BLUE, (0, 0, screen_width, screen_height))
        pygame.draw.rect(screen, Colors.GROUND_BROWN, (0, screen_height // 2 - player.z_rotation, 
                                                    screen_width, screen_height // 2 + player.z_rotation))

        # Beregn grunnleggende strålebredde
        ray_width_float = screen_width / settings["num_rays"][0]
        accumulated_x = 0  

        # FASE 1: Cast rays for vegger og samle spillerrefleksjonsdata
        for i in range(settings["num_rays"][0]):
            ray_angle = player.angle - settings["fov"][0] / 2 + i * (settings["fov"][0]/settings["num_rays"][0])
            
            # Initial stråle for veggdeteksjon
            new_x, new_y, depth, cell, side = self.cast_ray(player.x, player.y, ray_angle, settings)

            # Hopp over hvis ingen treff
            if depth >= self.max_depth:
                next_x = math.floor((i + 1) * ray_width_float)
                accumulated_x = next_x
                continue

            # Fisheyelens-korreksjon, ville sett ut som gjennom en lense hvis ikke 
            depth *= math.cos(math.radians(ray_angle - player.angle))
            
            # Beregn nøyaktig strålebredde for denne kolonnen
            next_x = math.floor((i + 1) * ray_width_float)
            actual_ray_width = max(1, next_x - accumulated_x)
            
            # Lagre gjeldende stråles posisjon
            current_screen_x = accumulated_x
            
            # Start rekursiv vegggjengivelse
            self.draw_recursive_wall(
                screen, screen_height, player, settings, depth, 
                player.x, player.y, new_x, new_y, cell, side, 
                1, current_screen_x, actual_ray_width, self.mirror_alpha)
            
            # Oppdater horisontal posisjon for neste stråle
            accumulated_x = next_x
            
        # FASE 2: Tegn alle spillerrefleksjoner i en separat gjennomgang
        self.render_player_reflections(screen, player, settings, screen_height)
    
    def render_player_reflections(self, screen, player, settings, screen_height):
        """
        Tegn alle samlede spillerrefleksjoner på toppen av senen.
        Grupperer tilstøtende refleksjoner for bedre kvalitet.
        """
        if not self.player_reflections:
            return
            
        # Sorter etter dybde og speilnivå (fjernest først)
        sorted_reflections = sorted(
            self.player_reflections, 
            key=lambda r: (r.depth, r.mirror_level), 
            reverse=True
        )
        
        # Grupper tilstøtende refleksjoner etter lignende dybde og speilnivå
        reflection_groups = []
        current_group = [sorted_reflections[0]]
        
        # Maksimalt tillatt mellomrom mellom refleksjoner som skal regnes som kontinuerlige (i pixler)
        max_gap = 2
        
        # Grupper tilstøtende refleksjoner
        for i in range(1, len(sorted_reflections)):
            current = sorted_reflections[i]
            previous = current_group[-1]
            
            # Sjekk om refleksjoner er fra samme dybdenivå, speilnivå, og tilstøtende på skjermen
            same_depth = abs(current.depth - previous.depth) < 30
            same_mirror = current.mirror_level == previous.mirror_level
            adjacent = (current.screen_x - (previous.screen_x + previous.width)) <= max_gap
            
            if same_depth and same_mirror and adjacent:
                # Legg til i gjeldende gruppe hvis tilstøtende
                current_group.append(current) 
            else:
                # Start en ny gruppe
                reflection_groups.append(current_group)
                current_group = [current]
        
        # Legg til den siste gruppen
        if current_group:
            reflection_groups.append(current_group)
        
        # Tegn hver gruppe som en enkelt spillerrefleksjon
        for group in reflection_groups:
            if not group:
                continue
            
            # Bruk gjennomsnittlig dybde
            avg_depth = sum(r.depth for r in group) / len(group)
            # Beregn spillerhøyde med avstandsskalering
            player_depth = max(0.1, avg_depth)
            player_height = (screen_height / (player_depth / 35 + 0.1) / (settings["fov"][0]/90)) * 0.6
            player_height = max(1, min(int(player_height), 5000))
            
            # Beregn total bredde for denne gruppen
            leftmost_x = min(r.screen_x for r in group)
            rightmost_x = max(r.screen_x + r.width for r in group)
            total_width = rightmost_x - leftmost_x
            
            # Posisjoner spilleren korrekt i forhold til horisontlinjen
            # Horisontlinjen er der objekter i uendelig avstand møter bakken
            horizon_y = screen_height / 2 - player.z_rotation
            
            # Eksponentiell reduksjon i vertikal justering
            scale_factor = 1600
            vertical_factor = scale_factor / (avg_depth + scale_factor)  # 1/x-forhold
            vertical_offset = player_height * vertical_factor
            
            # Beregn endelig top_y-posisjon
            top_y = horizon_y + vertical_offset - player_height
            
            # Blå spillerfarge, med høyere gjennomsiktighet etter refleksjoner
            mirror_level = group[0].mirror_level
            transparency = max(50, min(200, 200 - mirror_level * 10))
            player_color = (0, 0, 255, transparency)
            
            # Opprett en overflate for hele denne gruppen
            line_surface = pygame.Surface((total_width, player_height), pygame.SRCALPHA)
            pygame.draw.rect(line_surface, player_color, (0, 0, total_width, player_height))
            
            # Tegn som en enkelt enhet
            screen.blit(line_surface, (leftmost_x, top_y))

    def reflect_vector(self, v_x, v_y, side):
        """
        Beregner refleksjonsvektoren for en gitt innkommende vektor og side.
        Brukes for speilrefleksjoner
        """
        if side == "LEFT":  
            n_x, n_y = 1, 0
        elif side == "RIGHT":  
            n_x, n_y = -1, 0
        elif side == "TOP":
            n_x, n_y = 0, 1
        elif side == "BOTTOM":
            n_x, n_y = 0, -1
        else:
            raise ValueError("Ugyldig side for refleksjon")
 
        magnitude_n = math.sqrt(n_x**2 + n_y**2)
        n_x, n_y = n_x / magnitude_n, n_y / magnitude_n
 
        dot_product = v_x * n_x + v_y * n_y
 
        r_x = v_x - 2 * dot_product * n_x
        r_y = v_y - 2 * dot_product * n_y
 
        return r_x, r_y
 
    def angle_of_vector(self, v_x, v_y):
        """
        Beregner vinkelen til en vektor i radianer og grader.
        Brukes for å bestemme refleksjonsvinkler.
        """
        angle_rad = math.atan2(v_y, v_x)
        angle_deg = math.degrees(angle_rad)
        return angle_rad, angle_deg
 
    def draw_fps(self, screen, clock, font):
        """Tegner FPS til spillet på skjermen."""
        fps = clock.get_fps()
        fps_text = font.render(f"FPS: {fps:.0f}", True, (255, 255, 255))
        screen.blit(fps_text, (10, 10))
    
    def check_visibility(self, x1, y1, x2, y2):
        """Sjekker om det er direkte synslinje mellom to punkter (x1,y1) og (x2,y2)."""
        # Beregn retningsvektor
        dx = x2 - x1
        dy = y2 - y1
        
        # Beregn lengden av strålen
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Hvis punktene er praktisk talt identiske, er de synlige for hverandre
        if distance < 0.0001:
            return True
        
        # Normaliser retningsvektor
        if distance > 0:
            dx /= distance
            dy /= distance
        
        # Nåværende posisjon langs strålen (starter ved spillerens posisjon)
        ray_x, ray_y = x1, y1
        
        # Hvor mye å bevege seg langs stråle hver iterasjon
        step_size = max(0.1, min(self.cell_size / 20, distance / 10))
        
        # Beregn antall steg, sikre at det er minst 1
        steps = max(1, int(distance / step_size))
        
        # Beveg langs strålen og sjekk for vegger
        for _ in range(steps):
            ray_x += dx * step_size
            ray_y += dy * step_size
            
            # Hent rutenettkoordinater
            cell_x = int(ray_x // self.cell_size)
            cell_y = int(ray_y // self.cell_size)
            
            # Sjekk om vi er innenfor en gyldig celle i labyrinten
            if 0 <= cell_y < len(self.maze) and 0 <= cell_x < len(self.maze[0]):
                # Sjekk om cellen inneholder en vegg (verdi >= 1)
                if self.maze[cell_y][cell_x] >= 1:
                    return False  # Vegg oppdaget, ingen synslinje
            else:
                # Vi er utenfor labyrintens grenser
                return False
        
        # Ingen vegger oppdaget langs strålebanen
        return True
    
    def draw_entities(self, screen, player, entities, settings, screen_width, screen_height):
        """
        Tegner monstre i 3Dscenen.
        Håndterer dybdesortering, synlighet og perspektivskalering.
        """
        # Liste for å samle synlige monstre med avstandsinformasjon
        visible_monsters = []
        
        # Første gjennomgang: Samle alle synlige monstre
        for entity in entities:
            if entity.entity_type == "monster":
                # Beregn vinkel og avstand til monsteret
                dx = entity.x - player.x
                dy = entity.y - player.y
                distance = math.sqrt(dx*dx + dy*dy)
               
                # Hopp over hvis for langt unna
                if distance > settings["render_distance"][0]:
                    continue
               
                # Beregn vinkel til monsteret i forhold til spillerens visning
                angle_to_entity = math.degrees(math.atan2(dy, dx))
                angle_diff = (angle_to_entity - player.angle + 180) % 360 - 180
               
                # Hopp over hvis utenfor FOV
                if abs(angle_diff) > settings["fov"][0] / 2:
                    continue
                   
                # Sjekk om monsteret er synlig
                is_visible = self.check_visibility(player.x, player.y, entity.x, entity.y)
                if not is_visible:
                    continue
                
                # Beregn korrigert avstand for sortering, tar hensyn til fisheyelens effekten
                corrected_distance = distance * math.cos(math.radians(angle_diff))
                
                # Legg til i listen av synlige monstre
                visible_monsters.append((entity, distance, angle_diff, corrected_distance))
        
        # Sorter monstre etter avstand, lengst unna først (bakerst til fremst)
        visible_monsters.sort(key=lambda x: x[3], reverse=True)
        
        # Andre gjennomgang: Tegn monstre i sortert rekkefølge
        for monster_data in visible_monsters:
            entity, distance, angle_diff, corrected_distance = monster_data
               
            # Beregn skjermposisjon
            ray_pos = int((angle_diff + settings["fov"][0] / 2) / settings["fov"][0] * settings["num_rays"][0])
               
            # Beregn monsterhøyde på skjermen
            entity_height = screen_height / (corrected_distance / 25 + 0.1) / (settings["fov"][0]/90)
            entity_width = entity_height * 0.6  # størrelsesforhold
               
            # Beregn x-posisjon på skjermen
            x_pos = screen_width * ray_pos / settings["num_rays"][0] - entity_width / 2
               
            # Beregn y-posisjon, justert for spillerens z-rotasjon
            y_pos = screen_height / 2 - entity_height / 2 - player.z_rotation
               
            # Beregn farge basert på avstand
            color_intensity = min(255, int(255 / (1 + distance * 0.005)))
            intensity_factor = color_intensity / 255
            monster_color = (
                int(entity.color[0] * intensity_factor),
                int(entity.color[1] * intensity_factor),
                int(entity.color[2] * intensity_factor)
            )
               
            # Opprett en surface for monsteret
            entity_width = max(1, int(entity_width))
            entity_height = max(1, int(entity_height))
            
            monster_surface = pygame.Surface((entity_width, entity_height), pygame.SRCALPHA)
           
            # Tegn monsterkropp
            pygame.draw.ellipse(monster_surface, monster_color,
                            (entity_width * 0.25, 0, max(1, entity_width * 0.5), max(1, entity_height * 0.3)))  # Hode
            pygame.draw.rect(monster_surface, monster_color,
                            (entity_width * 0.3, entity_height * 0.3, max(1, entity_width * 0.4), max(1, entity_height * 0.4)))  # Kropp
           
            # Legg til øyne hvis nærme nok
            if entity_height > 30:
                eye_color = (255, 255, 255)
                pygame.draw.circle(monster_surface, eye_color,
                                (int(entity_width * 0.4), int(entity_height * 0.15)), max(1, int(entity_width * 0.06)))
                pygame.draw.circle(monster_surface, eye_color,
                                (int(entity_width * 0.6), int(entity_height * 0.15)), max(1, int(entity_width * 0.06)))
               
                # Legg til pupiller hvis nærme nok
                if entity_height > 60:
                    pupil_color = (0, 0, 0)
                    pygame.draw.circle(monster_surface, pupil_color,
                                    (int(entity_width * 0.4), int(entity_height * 0.15)), max(1, int(entity_width * 0.03)))
                    pygame.draw.circle(monster_surface, pupil_color,
                                    (int(entity_width * 0.6), int(entity_height * 0.15)), max(1, int(entity_width * 0.03)))
           
            # Tegn bein
            pygame.draw.rect(monster_surface, monster_color,
                            (entity_width * 0.2, entity_height * 0.5, max(1, entity_width * 0.2), max(1, entity_height * 0.5)))  # Venstre ben
            pygame.draw.rect(monster_surface, monster_color,
                            (entity_width * 0.6, entity_height * 0.5, max(1, entity_width * 0.2), max(1, entity_height * 0.5)))  # Høyre ben
           
            # Legg til monsteret på skjermen hvis det er synlig
            if x_pos + entity_width > 0 and x_pos < screen_width and y_pos + entity_height > 0 and y_pos < screen_height:
                screen.blit(monster_surface, (x_pos, y_pos))
 
class GameStateManager:
    """
    Håndterer Gamestates og overganger mellom dem.
    """
    def __init__(self, initial_state):
        self.current_state = initial_state
 
    def get_state(self):
        return self.current_state
 
    def set_state(self, state):
        self.current_state = state
 
class GameState:
    """
    Gamestate for 3D visning av spillet.
    Håndterer rendering av 3D scenen med entities.
    """
    def __init__(self, raycaster, player, monsters=None):
        self.raycaster = raycaster
        self.player = player
        self.monsters = monsters or []  
 
    def run(self, screen, clock, font, settings, screen_width, screen_height):
        """Kjører spillets 3D visning."""
        self.raycaster.draw_3d_scene(screen, self.player, settings, screen_width, screen_height)
        if self.monsters:
            self.raycaster.draw_entities(screen, self.player, self.monsters, settings, screen_width, screen_height)
        self.raycaster.draw_fps(screen, clock, font)
 
class MapState:
    """
    Gamestate for map.
    Viser labyrinten ovenfra med stråler og entities.
    """
    def __init__(self, raycaster, player, monsters=None):
        self.raycaster = raycaster
        self.player = player
        self.monsters = monsters or []
 
    def run(self, screen, clock, font, settings, screen_width, screen_height):
        """Kjører spillets mapstate."""
        self.raycaster.draw_minimap(screen, self.player)
        self.raycaster.draw_rays(screen, self.player, settings)
       
        # Tegn monstre på minimap
        for monster in self.monsters:
            pygame.draw.circle(screen, Colors.RED, (int(monster.x), int(monster.y)), 5)
 
class MenuState:
    """
    Gamestate for hovedmenyen.
    Håndterer map-valg og spillavslutning.
    """
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0
        self.last_key_press = {}
        self.title_font = pygame.font.Font(None, 72)
        self.menu_font = pygame.font.Font(None, 48)
        self.maps = [
            {"name": "Klassisk Labyrint", "description": "En tradisjonell labyrint med speil og monstre"},
            {"name": "Liten Arena", "description": "En kompakt arena"},
            {"name": "Speilpalass", "description": "En labyrint full av speil"},
            {"name": "Avslutt Spill", "description": "Avslutt applikasjonen"}
        ]
        self.title_y = 100
       
    def handle_event(self):
        """
        Håndterer brukerinput i menyen.
        Returnerer valgt handling (kartindeks eller 'exit').
        """
        keys = pygame.key.get_pressed()
       
        def key_pressed(key):
            if keys[key] and not self.last_key_press.get(key, False):
                self.last_key_press[key] = True
                return True
            if not keys[key]:
                self.last_key_press[key] = False
            return False
       
        if key_pressed(pygame.K_UP):
            self.selected_index = (self.selected_index - 1) % len(self.maps)
           
        if key_pressed(pygame.K_DOWN):
            self.selected_index = (self.selected_index + 1) % len(self.maps)
           
        if key_pressed(pygame.K_RETURN):
            if self.selected_index == len(self.maps) - 1:  # Avslutt spill alternativ
                return "exit"
            else:
                return self.selected_index
           
        return None
       
    def draw(self, screen):
        """Tegner menyen med interaktive elementer."""
       
        # Tegn bakgrunn
        background = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        background.fill((0, 0, 0))
        screen.blit(background, (0, 0))
       
        # Tegn tittel
        title = self.title_font.render("RAYCASTER LABYRINT", True, Colors.WHITE)
        title_rect = title.get_rect(center=(self.screen_width // 2, self.title_y))
        screen.blit(title, title_rect)
       
        # Tegn menyalternativer
        for i, map_option in enumerate(self.maps):
            color = Colors.MENU_HIGHLIGHT if i == self.selected_index else Colors.WHITE
            option_text = self.menu_font.render(map_option["name"], True, color)
           
            # Posisjoner alternativer i sentrum med mellomrom
            y_position = self.screen_height // 2 - len(self.maps) * 30 + i * 60
            option_rect = option_text.get_rect(center=(self.screen_width // 2, y_position))
            screen.blit(option_text, option_rect)
           
            # Tegn beskrivelse for valgt element
            if i == self.selected_index:
                desc_font = pygame.font.Font(None, 32)
                desc_text = desc_font.render(map_option["description"], True, (200, 200, 200))
                desc_rect = desc_text.get_rect(center=(self.screen_width // 2, y_position + 35))
                screen.blit(desc_text, desc_rect)
               
        # Tegn instruksjoner
        instructions = pygame.font.Font(None, 28).render(
            "Bruk OPP/NED-piltaster for å velge og ENTER for å bekrefte", True, (180, 180, 180))
        instructions_rect = instructions.get_rect(center=(self.screen_width // 2, self.screen_height - 50))
        screen.blit(instructions, instructions_rect)
 
class SettingsState:
    """
    Håndterer innstillingsskjermen i spillet.
    Lar brukeren justere grafiske innstillinger.
    """
    def __init__(self, width, height, settings, surface):
        self.screen_width = width
        self.screen_height = height
        self.surface = surface
        self.settings = settings
        self.show = False
        self.alpha = 50
        self.selected_index = 0  
        self.last_key_press = {}
       
        # Legg til tilbake til meny-alternativ
        self.menu_option = {"return_to_menu": [False, False, True]}
 
    def draw_settings_menu(self):
        """Tegner innstillingsmenyen med justerbare parametre."""
        menu_width, menu_height = int(self.screen_width * 0.8), int(self.screen_height * 0.8)
        menu_x, menu_y = (self.screen_width - menu_width) // 2, (self.screen_height - menu_height) // 2
 
        settings_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        settings_surface.fill((0, 0, 0, self.alpha))
 
        font = pygame.font.Font(None, 36)
        title_text = font.render("Innstillingsmeny", True, Colors.WHITE)
        settings_surface.blit(title_text, (menu_width // 2 - title_text.get_width() // 2, 30))
        aa_levels = ["Av", "Lav", "Middels", "Høy", "Ultra"]
        # Tegn vanlige innstillinger
        for i, key in enumerate(self.settings):
            color = Colors.WHITE if i == self.selected_index else (150, 150, 150)
           
            if key == "antialiasing":
                text_content = f"{key}: {aa_levels[self.settings[key][0]]} ({self.settings[key][0]})"
            else:
                text_content = f"{key}: {self.settings[key][0]}"
 
            text = font.render(text_content, True, color)
            settings_surface.blit(text, (50, 100 + i * 40))
       
        # Tegn "Tilbake til meny" alternativ
        total_options = len(self.settings)
        return_color = Colors.WHITE if total_options == self.selected_index else (150, 150, 150)
        return_text = font.render("Tilbake til hovedmeny", True, return_color)
        settings_surface.blit(return_text, (50, 100 + total_options * 40))
 
        self.surface.blit(settings_surface, (menu_x, menu_y))
 
    def handle_event(self):
        """
        Håndterer brukerinput i innstillingsmenyen.
        Returnerer oppdaterte innstillinger eller signal om å gå tilbake til hovedmenyen.
        """
        keys = pygame.key.get_pressed()
        setting_keys = list(self.settings.keys())
        total_options = len(setting_keys) + 1  # +1 for "Tilbake til meny"
 
        def key_pressed(key):
            if keys[key] and not self.last_key_press.get(key, False):
                self.last_key_press[key] = True
                return True
            if not keys[key]:
                self.last_key_press[key] = False
            return False
           
        if keys[pygame.K_LSHIFT]:
            delta_setting = 5
        else:
            delta_setting = 1
 
        if key_pressed(pygame.K_UP):
            self.selected_index = max(0, self.selected_index - 1)
 
        if key_pressed(pygame.K_DOWN):
            self.selected_index = min(total_options - 1, self.selected_index + 1)
 
        if self.selected_index == 4: # anti aliasing
            key = setting_keys[self.selected_index]
            if key_pressed(pygame.K_LEFT):
                self.settings[key][0] = max(self.settings[key][1], self.settings[key][0] - 1)
 
            if key_pressed(pygame.K_RIGHT):
                self.settings[key][0] = min(self.settings[key][2], self.settings[key][0] + 1)
 
        # Håndter venstre/høyre for å justere innstillinger
        else:
            if self.selected_index < len(setting_keys):
                key = setting_keys[self.selected_index]
                if keys[pygame.K_LEFT]:
                    self.settings[key][0] = max(self.settings[key][1], self.settings[key][0] - delta_setting)
   
                if keys[pygame.K_RIGHT]:
                    self.settings[key][0] = min(self.settings[key][2], self.settings[key][0] + delta_setting)
   
        # Håndter Enter for "Tilbake til meny" alternativ
        if key_pressed(pygame.K_RETURN) and self.selected_index == len(setting_keys):
            return "menu"  # Signal om å gå tilbake til menyen
 
        if key_pressed(pygame.K_ESCAPE):
            self.show = False
           
        return self.settings
 
class MazeLoader:
    """
    Klasse for å lagre forskjellige maps.
    Inneholder predefinerte labyrintdesign.
    """
    @staticmethod
    def get_maze(index):
        """Returnerer en forhåndsdefinert labyrint basert på indeks."""
        mazes = [
            # Klassisk Labyrint
            [
                [3, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 1],
                [1, 0, 1, 1, 0, 2, 0, 1, 1, 1, 0, 1],
                [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
                [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
                [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
                [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1],
                [1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1],
                [1, 2, 2, 1, 0, 1, 1, 1, 0, 1, 1, 1],
                [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            ],
            # Liten Arena
            [
                [1, 1, 1, 1, 1, 1, 1, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 3, 0, 0, 3, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 0, 2, 2, 0, 0, 1],
                [1, 0, 3, 0, 0, 3, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 1, 1, 1, 1, 1, 1, 1],
            ],
            # Speilpalass
            [
                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                [2, 0, 2, 0, 0, 0, 0, 2, 0, 2],
                [2, 0, 2, 0, 2, 2, 0, 2, 0, 2],
                [2, 0, 2, 0, 2, 2, 0, 2, 0, 2],
                [2, 0, 0, 0, 0, 0, 0, 0, 0, 2],
                [2, 0, 2, 2, 0, 0, 2, 2, 0, 2],
                [2, 0, 2, 0, 0, 0, 0, 2, 0, 2],
                [2, 0, 2, 0, 2, 2, 0, 2, 0, 2],
                [2, 0, 0, 0, 0, 0, 0, 0, 0, 2],
                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            ]
        ]
        return mazes[index]
 
class Game:
    """
    Hovedklasse som kjører spillet.
    Håndterer initialisering, spilløkke og overganger.
    """
    def __init__(self):
        """Initialiserer spillet og setter opp hovedkomponenter."""
        
        
        # Initialiser display og få dimensjoner
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_width, self.screen_height = self.screen.get_size()
        pygame.display.set_caption("Raycasting")
 
        # Initialiser timing
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.FPS = 30
        self.running = True
       
        # Standardinnstillinger
        self.cell_size = 50
        self.fov = 90
        self.num_rays = 512
        self.render_distance = 1000
 
        self.settings = {
            "num_rays": [self.num_rays, 1, 2000],
            "fov": [self.fov, 30, 120],
            "render_distance": [self.render_distance, 50, 2000],
            "fps": [self.FPS, 1, 144],
            "antialiasing": [2, 0, 4]  # 0: Av, 1: Lav, 2: Middels, 3: Høy, 4: Ultra
        }
       
        # Initialiser Gamestates
        self.menu_state = MenuState(self.screen_width, self.screen_height)
        self.settings_menu = SettingsState(self.screen_width, self.screen_height, self.settings, self.screen)
       
        # Initialiser Gamestate, med "menu" som start
        self.game_state_manager = GameStateManager("menu")
       
        # Initialiserer Gamestates når et map er valgt
        self.states = {}
       
        # Start spilløkken
        self.run()
       
    def initialize_game_states(self, maze_index):
        """
        Initialiserer Gamestates med valgt labyrint.
        Setter opp raycaster, spiller og monstre basert på labyrintdesign.
        """
        # Hent labyrintlayout
        maze = MazeLoader.get_maze(maze_index)
       
        # Initialiser raycaster med labyrinten
        self.raycaster = Raycaster(maze, self.cell_size, self.settings["fov"][0],
                                self.settings["num_rays"][0], self.settings["render_distance"][0])
       
        # Initialiser spiller og monstre
        self.player = Player(maze, self.raycaster)
       
        # Juster antall monstre basert på labyrintstørrelse
        num_monsters = max(1, min(5, (len(maze) * len(maze[0])) // 30))
        # num_monsters = 100
        self.monsters = [Monster(maze, self.raycaster) for _ in range(num_monsters)]
       
        # Initialiser gamestates
        self.states = {
            "game": GameState(self.raycaster, self.player, self.monsters),
            "map": MapState(self.raycaster, self.player, self.monsters),
        }
       
        # Overskriver settings slik at de blir tilbakestilt til neste map
        self.settings_menu = SettingsState(self.screen_width, self.screen_height, self.settings, self.screen)
   
    def handle_events(self):
        """Håndterer alle spillhendelser og brukerinput."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Sjekk for TAB for å veksle mellom spill og map
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    if self.game_state_manager.get_state() in ["game", "map"]:
                        new_state = "map" if self.game_state_manager.get_state() == "game" else "game"
                        self.game_state_manager.set_state(new_state)
                
                # Veksle ray visablity med R når i map
                elif event.key == pygame.K_r:
                    if self.game_state_manager.get_state() in "map":
                        self.raycaster.show_rays = not self.raycaster.show_rays
            
            # Veksle innstillingsmeny
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                current_state = self.game_state_manager.get_state()
                    
                if current_state in ["game", "map"]:
                    if not self.settings_menu.show:
                        self.settings_menu.show = True
                    else:
                        self.settings_menu.show = False
                elif current_state == "menu":
                    # ESC fra hovedmenyen avslutter spillet
                    self.running = False
 
    def run(self):
        """
        Hovedspilløkke.
        Håndterer gamestates, oppdatering og rendering.
        """
        while self.running:
            self.screen.fill(Colors.BLACK)
           
            current_state = self.game_state_manager.get_state()
           
            if current_state == "menu":
                # Tegn menyen og håndter menyhandlinger
                self.menu_state.draw(self.screen)
                menu_action = self.menu_state.handle_event()
               
                if menu_action == "exit":
                    self.running = False
                elif menu_action is not None:  # Et map ble valgt
                    self.initialize_game_states(menu_action)
                    self.game_state_manager.set_state("game")
                   
            elif current_state in ["game", "map"]:
                # Håndter innstillingsmeny
                if self.settings_menu.show:
                    # Tegn gamestaten først
                    self.states[current_state].run(self.screen, self.clock, self.font, self.settings, 
                                                self.screen_width, self.screen_height)
                   
                    # Tegn deretter innstillingsmenyen på toppen
                    result = self.settings_menu.handle_event()
                    self.settings_menu.draw_settings_menu()
                   
                    # Sjekk om vi trenger å gå tilbake til hovedmenyen
                    if result == "menu":
                        self.game_state_manager.set_state("menu")
                        self.settings_menu.show = False
                else:
                    # Oppdater spillerposisjon
                    self.player.move()
                   
                    # Oppdater monstre med kollisjonsdeteksjon
                    for monster in self.monsters:
                        monster.update(self.player, self.monsters)
                   
                    # Tegn current gamestate
                    self.states[current_state].run(self.screen, self.clock, self.font, self.settings, 
                                                self.screen_width, self.screen_height)
           
            self.handle_events()
            pygame.display.flip()

            # Spillet kjører med FPS satt i settings
            self.clock.tick(self.settings["fps"][0])
           
        pygame.quit()
 
if __name__ == "__main__":
    Game()  # Lager Game instans og kjører spillet
