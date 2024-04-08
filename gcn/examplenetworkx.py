import networkx as nx
import matplotlib.pyplot as plt

#G = nx.Graph #Do thi vo huong
G = nx.DiGraph() #Do thi co huong

#Them cac node vao do thi
G.add_nodes_from(
    [
        (0,{"color": "blue", "size": 650}),
        (1,{"color": "green", "size": 650}),
        (2,{"color": "red", "size": 650}),
    ]
)

G.add_edges_from(
    [
        (0,1),
        (0,2),
        (1,2)
    ]
)

#in ra man hinh danh sach cac node
for node in G.nodes(data=True):
    print(node)

#ve cac node ra man hinh
node_color = nx.get_node_attributes(G,"color").values()
colors = list(node_color)
node_size = nx.get_node_attributes(G,"size").values()
sizes = list(node_size)
nx.draw(G,with_labels = True, node_color=colors, node_size=sizes)
plt.waitforbuttonpress()

