# DNS-Load-Balancer

A load balancing system divides incoming requests among multiple servers. One approach to deploy load balancing is using DNS servers. In this approach, the website manager (e.g., www.example.com) installs multiple web servers to serve clients. Each server has a specific public IP address. When a client wants to find the IP address of the website (wwww.example.com), the DNS server chooses one of the web servers based on the load balancing policy and returns the IP address.

1.	Created multiple web server instances (minimum three) using Amazon AWS or any other cloud provider. Servers are placed in different regions. 
2.	Registered a domain name for your website.
3.	Installed a DNS server resolving the domain name.
4.	Configured the DNS server to enable us to specify the list of IP addresses for the multiple instances of the web servers (you created in Step 1) and a load balancing algorithm as inputs. As a result, the web clients end up directing their HTTP requests to the servers to balance the load with the given algorithm.
5.	Measured the performance of the load balancing algorithm. Identified the metrics that are meaningful for such measurements before starting the experiments.

Load balancing algorithm

Implemented three different load balancing algorithms:

1.	Round-robin: each time a client wants to resolve the domain name, the DNS server chooses the server based on the round-robin approach.
2.	Geological approximation: each client connects to the web server deployed within that region.  If there is no web server in that region, the DNS server randomly chooses a server to resolve the domain name.
3.	Load-based: each web server tells the DNS server how many clients it can handle. The DNS server chooses the servers based on the round-robin approach to resolve the domain name, however, this time DNS server uses the same IP address for clients until the number of requests for that server reaches a threshold. Then the DNS server returns the next IP address in the list.

 
Performance evaluation of the project
1.	The load balancing system works for all the clients that are connected to the Internet. The system makes sure that all clients are connected to a web server.
2.	The system generates a report on how requests were distributed among different servers.
3.	The system changes the time-to-live of the DNS record and measure the impact on the performance of load balancing.
