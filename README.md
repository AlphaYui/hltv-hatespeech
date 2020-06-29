# hltv-hatespeech

This is part of a small data science project.
The program scrapes the hltv.org forums for new messages and analyzes those using the hatesonar library. Each message receives a confidence rating that it contains hatespeech. These results are stored in an SQL database for later analysis. Each message is associated with an author, thread and forum, so that they can later be linked.

Using this data, we hope to find correlations between certain user groups and hatespeech. The research question of this work can be summarized as follows:
1. Do the HLTV.org off-topic forum and the HLTV forums in general have a statistically significant increase in hatespeech compared to other communities?
2. If so, can these issues be narrowed down to a certain user group?
3. Are there concrete measures that can be taken to improve the HLTV forums to minimize hatespeech?

The following three sub-forums are observed:
- Off-Topic
- Counterstrike: Global Offensive
- Hardware & Tweaks

Additionally, a second program analyzes messages in a Rocket League Discord server. The purpose of this is to compare HLTV's overall performance with the one of a tightly moderated community.
More control groups from other gaming-related forums could be added in the future. As the hatesonar-model has a high rate of false classifications (both positive and negative), this is required to show that there are significant differences between HLTV Off-Topic and other communities.

NOTE: As this project has been thrown together in a short amount of time (in reaction to recent discussions regarding the existence of the HLTV-forums), it is not very well documented and implemented. Especially the Discord bot is currently only suited for use in one specific server. Hopefully this can be improved in the future.
