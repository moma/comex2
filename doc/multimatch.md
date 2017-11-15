## Multimatch principles overview

Before summer 2017 the maps of community explorer were always matching **scholars** with their **keywords**.
  - the database had other types of data entities available
    - countries, labs, institutions, jobs
  - a mission of the summer 2017 was to find a generalization of the matching principle to match the other entities

#### Chosen theoretical perspective (in french)

  1. ProjectExplorer est un outil pour visualiser des relations associatives
  2. La combinaison de plusieurs relations est une relation
    - (scholar ↔ lab) x (scholar ↔ keyword) donne une relation lab ↔ keyword
  3. En général on peut distinguer deux familles de relations associatives en *« text et data mining »*:
    - **match SW**: les relations par prédication (on stipule que entité A est liée à entité B)
       - ce sont des relations à la RDF, typique des bases structurées et du Semantic Web (SW)
       - par exemple : l'utilisateur X habite dans le pays A
    - **match IR**: les relations par corrélation statistique ou stochastiques (coocurrences, corrélations, etc)
       - ce sont des relations de similarité sur une métrique, typiques des bases non- ou semi-structurées et des moteurs de recherches documentaires (IR)
       - par exemple : l'utilisateur X utilise souvent les termes α, β
       - autre exemple particulier à notre cas : la majorité des utilisateurs du labo B habitent dans le pays A
  4. Potentiellement, ces relations peuvent être combinées entre elles à l'infini pour mettre au jour des relations nouvelles
  5. Notre implémentation du multimatch n'ira pas à ce niveau de généricité (on va surtout utiliser scholar comme objet pivôt), mais cette idée est en arrière-plan

**In our case, *scholar* as main pivot object**
 The data model of community explorer allows us to almost always be able to relate two pieces of data via scholars, because the scholars table is central to the data structure (cf. figure)

![Image of DB objects and their relationship](https://raw.githubusercontent.com/moma/comex2/master/doc/comex_obj_rels.png)


#### Implementation as operations on M  [type X <=> pivot]
We can always consider the relationships in matrix representation:
  - **`M1 [source_type x filtered_pivots]`**
  - **`M2 [filtered_pivots x target_type]`**


###### Bipartite neigbors
The product will correspond to the cross-relations XR:

 `M1 o M2 = XR [source_type x target_type]`      aka "bipartite neighbors"
                                                    in ProjectExplorer

For instance if I want the relationship between keywords and labs I'd use:
  - `M1 [keyword x scholars]`
  - `M2 [scholars x labs]`
  - `M1 o M2` gives us the bipartite links `XR [keyword x labs]`


###### Same-side neigbors
We will have two possibilities to build the "sameside neighbors"
(let Neighs_11 represent them within type 1, Neighs_22 within type 2)

**(i)** using all transitions (ie via pivot edges and via opposite type edges)
```
Neighs_11 = XR o XR⁻¹   = (M1 o M2)   o (M1 o M2)⁻¹
Neighs_22 = XR⁻¹ o XR   = (M1 o M2)⁻¹ o (M1 o M2)
```

For instance, a `lab_A -- lab_B` neighbor link is found by following **4** DB links:
  - **lab_A** -> scholars and scholars -> keywords
    - it's `(M1 o M2)⁻¹`
  - keywords -> scholars and scholars -> **lab_B**
    - it's `(M1 o M2)`

**(ii)** or using pivot edges only
```
Neighs_11 = M1 o M1⁻¹
Neighs_22 = M2⁻¹ o M2
```

For instance, `kw_α -- kw_β` neighbor links are found by following **2** DB links:
  - **keyword α** -> scholars
    - it's `M1`
  - scholars -> **keyword β**
    - it's `M2`

In practice, we will use formula (ii) for Neighs_11 and formula (i)  for Neighs_22,
 because:
   - type_1 ∈ {kw, ht}

     The app's allowed **source types** (keywords **kw**, community hashtags **ht**) tend to have a **X-to-many** relationship with pivot
      - following only keyword-scholars edges already yields meaningful connections for `Neighs_11 [keywords x keywords]`)


   - type_2 ∈ {sch, lab, inst, country}

     The app's **target types** (scholars, labs, institutions, countries)
       + tend to have a **X-to-1** relationship with pivot (a scholar has usually one country, one lab...)
       - using pivot edges only wouldn't create much links

###### Weights
For *bipartite relationships*, `count(pivotID)` is our base **weight**.

For instance if we match keywords <=> laboratories, the weight of the  `kw_α -- lab_A` edge is the number of scholars from lab_A with kw_α.

And with the *sameside relationships*, the weighting uses 2 steps
  - coocurrence `cooc(α,β)` is defined as the **count of pivots that have BOTH α AND β**
  - and the normalized value `cooc(α,β)/(total(α) + total(β) - cooc(α,β))` is our edge weight (it is the jaccard formula adapted to our case).

For instance the weight of a `kw_α -- kw_β` edge is the total scholars that have both of them divided by the total scholars that have any of them (union in jaccard).


#### Implementation in the app
  - the corresponding multimatch SQL code is here in [`services/dbdatapi.py`](https://github.com/moma/comex2/blob/dc48d36/services/dbdatapi.py#L250)
  - the corresponding DB types are defined as classes in [`services/dbentities.py`](https://github.com/moma/comex2/blob/dc48d36/services/dbentities.py)
