1. Segment retrieved from cloud.
	1. Segment was never downloaded to an edge.
	2. Segment was downloaded to some edge server, but got evicted. (possibly multiple times).
2. Segment retrieved from edge.
	1. This edge node was calculated before hand.
	2. This edge node was deffered.	

CASE 1.1 - No retention, this is the default case.
CASE 1.2, 2.1, 2.2 - Track edge transfers seperately.
	1.2 - N evictions + 1 cloud download. Track the evictions and mark them as "false-eviction"
	2.1 - Calculate retention of the simple download. This is the base case.
	2.2 - N evictions + final transfer.
	
Hence there are two 3 types of events that should be tracked. All these are per user, per segment, per edge
1. C: Cloud download `TODO1`
2. E: Edge cache eviction `TODO2`
3. D: Edge download `TODO3`

UserId, SegmentId, EdgeId, DownloadClock, CloseClock, Retention

DownloadClock will store the time when the segment was retrieved into the edge.
CloseClock with store the time when the segment was downloaded by the userid or evicted from cache.
Retention = CloseClock - DownloadClock.

The retention of a segment should be independent of the user as segments may be shared.

SegmentId, EdgeId, min(DownloadClock), max(CloseClock), Effective Retention
Effective Retention = max(CloseClock) - min(DownloadClock)

In an ideal case, the minimum possible retention is given only by the path of the vehicles.
Ideal retention = max(requested by a client) - min(Requested by a client)

- The above definition will be 0 in case that segment is only requested once in an edge node. Procastination from cloud?
- This definition is per segment, per edge. How to extend that to either a route or the entire simulation? Weighted average?

> Hence a good measure of reducing redundancy is just excess retention = retention - idea retention. This is always in the tradeoff space between distributing the cloud's transfers with time vs aiming for ideal retention. Distributing cloud's transfer will result in less peak requirements for the cloud vs less peak requirements for the edge cache in case of ideal retention.

> We this have two metrics we can measure. Cloud bandwidth distribution vs Peak edge cache space. Since peak edge cache space is more "restrictive" as cache loss will result in more cloud bandwidth usage, so to measure this, we need to first have peak edge cache space vs peak cloud bandwidth. Then another metric to compare how a restrictive cache space results in the cloud being more and more utilized in a non-uniform way.

How to have best of both worlds?

### Define a k-factor (per edge) or a time factor (per route)

On the path, if the user reaches ith node, i+kth node is informed to download from the cloud. Idea here is that we want to go towards ideal retention while keeping cloud's access uniform. Also k depends upon the spacing between the edge nodes. Say there are 10 edge nodes per 10 mins in the route, k can be as kept large as we have some fallback options and the time for the next node is very early. In case there are only 2 edge nodes in 10 mins, then we can keep k = 1. This boils down to how the edge nodes are placed in the route. We can either keep a factor per edge (graph edge) which will say that if that user is going to be a part of this graph edge, then we need to have a small k. Time can also be used for this.

### Define a time/distance factor per route

Incorporating the velocity, we can calculate the next stop required?
