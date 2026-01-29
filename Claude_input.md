# Claude Input Messages

This file tracks all user messages in this conversation.

---

## Message 1

> Look at this branch https://github.com/githubgir/idm/tree/claude/implement-mvp-features-pfs2q and based off it tell me how much of the idea could have been implemented via Claude code/GitHub features.
>
> Eg instead of doing all of what I did I could have created a GitHub repo and a Claude code project and instructed Claude code to summarize message by message into the summary.md and after each step instructed it to store the incoming message in a new file, and push as a commit to a GitHub branch both the message and the updated summary.md. Then I would have all I need, right?
>
> Claude code is required because it is already operating as a diff on the files, not changing them unnecessaryly.
>
> At the usage stage, I would be going between commits using all the GitHub functionality.

---

## Message 2

> I mean if I need the speed I could extract the GitHub repo incl all commits into a sql storage for faster extraction. But then I would need to implement all the features myself
>
> Also please create and keep adding to the Claude_input.md all my messages here

---

## Message 3

> Ok. You meant before that if I want a programmatic workflow I would not be able to do it via Claude code/github? But I think I could, right? I can use both via an API, no? Can you create a diagram workflow how that could've automated via both apis?

---

## Message 4

> I am sure we can write a prompt to ask Claude code to identify different topics in one message and split it into chunks and summarize just one chunk at a time and do chunk commit, no?

---

## Message 5

> Take a look at my branch.
> Do not look again into the other branches mentioned, you already do that and it broke you. Please just read the analysis-mvp-automation.md.
> Initialise Claude.md to get an understanding of what is being done
> Then read the claude_input.md it contains my messages to Claude code which generated the analysis and check if all the messages there are already answered in the analysis md.
> As always add my msg to claude_input.md

---

## Message 6

> Can you help me create the full workflow for the Claude code/github version? Covering an MVP of automatic functions for
> - setup GitHub repo and Claude code project with names and descriptions and link them
> - get user to create and commit summary_spec for what and how to summarize
> - function that takes a new message and instructs Claude to work on the current branch to update the summary (it would then automatically load the current version of summary.md and the summary_spec.md from the repo, create the changes and commit)
> - function that would retrieve the summary.md diffs for a given message
> - then i need a visualisation still?

---

## Message 7

> Yes create the workflow spec
>
> Now based on this update the readme and create all the code. Please separate the code from prompt templates

---

## Message 8

> Can you also store this chat (my input and your responses) as an Claude_chat.md file and update it after each reply.

---

## Message 9

> Can we please clarify on point. I understood that I can use claude code as an API but maybe I am wrong. Did I understand it correctly that you suggestion (A) is: the script takes the message sends it to anthropic API to create the update the summary, then takes the full summary passes it to github, at which point github figures out what changed. This is different from my suggestion (B): I use claude code API, which is linked to the github repo and in my message I ask to summary the attached message, claude code will then use its tools to create the diff on the summary.md, not github inferring the diffs from orginal summary.md and the updated version, and then claude code usually commits at the end of each step. The reason being that I like claude code's diff-like updates for the summary and the commits.
>
> So please summarize all three options nicely in the readme.md, (A) and (B) and (C) the earlier full package implementation without github or claude code. Once you summarized, please say that we are going for (B) and implement B

---

## Message 10

> Read the prd.md, the claude_input.md, and the readme.md. Show me the completed and outstanding tasks. Check the code if completed tasks are actually completed.

---

## Message 11

> Just to be clear we are building the option (B)? Can you please rename this project into VeraChat. A chat summarisation versioning and tracking system

---

## Message 12

> 1) I want it to be reusable. Ie I will have several apps where I want to use it. Suggest how that would work
> 2) as a proof of concept I want to have a good looking UI which has a chat pane to chat with say chatGPT and for this chat I want the summary to be developed and change-tracked visually in the right pane. Ideally clicking on a chat message would highlight the portions of the summary that were changed; and the other way around highlighting a text in the summary would highlight the chat message specific bits that caused the summary to update.
> 3) keep adding my messages and this conversation to claude_input.md and claude_chat.md as we progress here

---

## Message 13

> I would suggest the functionality of the bidirectional highlighting needs to be split between the reusable core component and the "throw away" visualisation. I want to know how we split the messages and summary in chunks and link them to each other and if we use GitHub features to store these chunks or we use GitHub only to process and then export everything into sqllite?

---

## Message 14

> Ok let's code it up then!

---
