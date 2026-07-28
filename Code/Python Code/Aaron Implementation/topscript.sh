
for i in {1..5}
do
	./mainscript_astar_test.sh > intermediate_data/res_astar$i.csv
	./mainscript_bellman_ford_test.sh > intermediate_data/res_bellman$i.csv
	./mainscript_dijkstra_test.sh > intermediate_data/res_dijkstra$i.csv
	./mainscript_harmony_search_test.sh > intermediate_data/res_harmony$i.csv
done

python3 intermediate_data/csv_process.py intermediate_data/res_astar 5
python3 intermediate_data/csv_process.py intermediate_data/res_bellman 5
python3 intermediate_data/csv_process.py intermediate_data/res_dijkstra 5
python3 intermediate_data/csv_process.py intermediate_data/res_harmony 5
