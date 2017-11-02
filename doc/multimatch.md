## Multimatch principles overview

Before summer 2017 the maps of community explorer were always matching **scholars** with their **keywords**.
  - the database had other types of data entities available
    - countries, labs, institutions, jobs
  - a mission of the summer 2017 was to find a generalization of the matching principle to match the other entities

#### Chosen theoretical perspective (in french)

  1. ProjectExplorer est un outil pour visualiser des relations associatives
  2. La combinaison de plusieurs relations est une relation
    - (scholar ↔ lab) x (scholar ↔ keyword) donne une relation lab ↔ keyword
  3. En général je distingue deux familles de relations associatives en « text et data mining »:
    - SWMATCH : les relations par prédication (on stipule que entité A est liée à entité B)
      ce sont des relations à la RDF, typique des bases structurées et du Semantic Web
      par exemple : l'utilisateur X habite dans le pays A
    - IRMATCH : les relations par corrélation statistique ou stochastiques (coocurrences, corrélations, etc)
       - ce sont des relations de similarité sur une métrique, typiques des bases non- ou semi-structurées et des moteurs de recherches documentaires (IR)
       - par exemple : l'utilisateur X utilise souvent les termes α, β
       - autre exemple particulier à notre cas : la majorité des utilisateurs du labo B habitent dans le pays A
  4. Potentiellement, ces relations peuvent être combinées entre elles à l'infini pour mettre au jour des relations nouvelles
  5. Notre implémentation du multimatch n'ira pas à ce niveau de généricité (on va surtout utiliser scholar comme objet pivôt), mais cette idée est en arrière-plan

**In our case, *scholar* as main pivot object**
 The data model of community explorer allows us to almost always be able to relate two pieces of data via scholars, because the scholars table is central to the data structure (cf. figure)

![Image of DB objects and their relationship]
(https://github.com/moma/comex2/blob/master/doc/comex_obj_rels.png)


#### Implementation as operations on M  [type X <=> pivot]
We can always consider the relationships in matrix representation:
  - `M1 [source_type x filtered_pivots]`
  - `M2 [filtered_pivots x target_type]`

The SQL match_table built below will correspond to the cross-relations XR:

 `M1 o M2 = XR [source_type x target_type]`      aka "opposite neighbors"
                                                    in ProjectExplorer

Finally we will have two possibilities to build the "sameside neighbors"
(let Neighs_11 represent them within type 1, Neighs_22 within type 2)

(i) using all transitions (ie via pivot edges and via opposite type edges)
Neighs_11 = XR o XR⁻¹   = (M1 o M2)   o (M1 o M2)⁻¹
Neighs_22 = XR⁻¹ o XR   = (M1 o M2)⁻¹ o (M1 o M2)

(ii) or via pivot edges only
Neighs_11 = M1 o M1⁻¹
Neighs_22 = M2⁻¹ o M2

+results with (ii) are filtered by sources that matched a target (for 11)
                               or targets that matched a source (for 22)

In practice, we will use formula (ii) for Neighs_11 except if pivot is keywords,
                    and formula (i)  for Neighs_22,
 because:
   - type_1 ∈ {kw, ht}
     The app's allowed source_types (keywords, community tags) tend to
     have a ???-to-many relationship with pivot (following only pivot
     edges already yields meaningful connections for Neighs_11)

   - type_2 ∈ {sch, lab, inst, country}
     Allowed target_types (scholars, labs, orgs, countries) tend to have
     a ???-to-1 relation with pivot (a scholar has usually one country,
     one lab..) (using pivot edges only wouldn't create much links)

Finally count(pivotID) is our weight
 for instance: if we match keywords <=> laboratories
               the weight of the  kw1 -- lab2 edge is
               the number of scholars from lab2 with kw1

=> on obtient le croisement des 2 types.
Code SQL correspondant
cf. https://github.com/moma/comex2/blob/dc48d36/services/dbdatapi.py#L250
