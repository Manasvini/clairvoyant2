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
