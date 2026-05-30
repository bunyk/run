# Run

What you can not measure, you cannot improve. I don't think it's 100% true,
it's just you would not know if it is improving or not.

I'm not 100% satisfied with Strava, I was more of an Endomondo fan, but it died,
therefore, I've built a set of scripts to replace it. 

What here is better that Strava:

- Scripts are free, as in beer, and open source, as in freedom.
- Total privacy, your data is stored on your computer, so you even run on Aircraft carrier.
- Just important metrics.

Disadvantage - to compare yourself with friends you would need to
send them your data with PRs and stuff over email or by other means.


## Usage

Your data is stored in tcx files in `data/` folder.


### Heatmap

Run `python heatmap.py` to generate heatmap of your workouts, looking something similar to this:

![heatmap](heatmap.png)


### Connecting to Polar AccessLink API

Go to https://www.polar.com/accesslink-api/ to obtain your client id and secret, then store that values in following environment variables:

- `POLAR_CLIENT_ID`
- `POLAR_CLIENT_SECRET`

You could also store them in `my.env` file and load them with:

```
export $(cat my.env | xargs)
```

Then running `python fetch_polar.py` would download TCX files
for recent 30 days of workouts that you have not yet downloaded.
