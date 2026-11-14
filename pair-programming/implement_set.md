Test-Driven Pair Programming: Grow a Java Set Class from Unit Tests

Company: Ode

Role: Software Engineer

Category: Software Engineering Fundamentals

Difficulty: easy

Interview Round: Technical Screen
This screen is a test-driven pair-programming session. You do the thinking and talking; the interviewer does the typing. Together you build a set class in Java one small step at a time: for each set operation you first say which unit tests it needs, the interviewer writes them, and then you direct the smallest change to the class that makes the failing tests pass. The interviewer's guidance is "do the simplest thing that works". Runtime and memory complexity do not matter in this exercise, but the interviewer will keep challenging you on whether your implementation is really the simplest one that passes the current tests. For example, while `isEmpty()` is the only behavior under test, it can be implemented with a single boolean; nothing yet requires a data structure that stores elements. Further behavior is added to the class only when a test demands it. Because the interviewer types, the session is effectively language-agnostic for you: what is assessed is how clearly you express test cases and implementation steps, and how you debug together when a test fails. There is not enough time to implement every operation, so make sure the main ones are covered. The session ends with a verbal discussion of how you would expand the set. ### Constraints and Clarifications - The language is Java and the tests are unit tests; assume JUnit. - The exact list of operations was not fixed in advance. Assume a minimal set API such as `isEmpty()`, `add(x)`, `contains(x)`, `remove(x)` and `size()`, and confirm it with the interviewer. - Correctness is judged only by the tests written during the session, so any behavior you want must first appear as a test. ### Clarifying Questions - Which operations should the set support, and should `add` and `remove` return nothing, or a boolean saying whether the set changed, as `java.util.Set` does? - What element type should the set hold to start with: a fixed type such as `String`, or a generic type parameter? - Is `null` a legal element? If not, should adding it throw? - May the class delegate storage to a built-in collection such as `ArrayList`, or should it manage its own array? - Should two elements count as the same when they are `equals`, or only when they are the same object? ### Part 1 — Tests first Choose the order in which you will tackle the operations. For each operation, say which unit test cases you would write, in the order you would write them, and what each one checks. Name each test so that a failure message explains itself. ```hint Each test should force one change Order the cases so that every new test fails against the current code for exactly one reason. A test that already passes puts no pressure on the design; a test that fails for three reasons makes the next step too big. ``` ```hint Look past the happy path For each operation, think about an element that was never added, the same element added twice, an operation on an empty set, and what one operation does to the results of the others. ``` #### What This Part Should Cover - A sensible order of operations, starting from the one that needs the least state - For each operation, positive cases, negative cases and interactions with the other operations - Tests that are small, independent and named after the behavior they check - Edge cases: duplicates, removing an absent element, emptiness after removal, equality of distinct but equal objects ### Part 2 — The simplest implementation that passes Starting from an empty class, direct the interviewer through the changes that make each new test pass. At every step, justify why your change is the simplest one that turns the current failing test green without breaking earlier tests, and say when a refactor is due. ```hint Let a later test break your shortcut Start with the shortcut the interviewer suggested. Then look for the later test that makes that shortcut give a wrong answer, and decide what the minimal replacement is at that moment. ``` #### Clarifying Questions for this Part - When a new test forces a bigger change, may you first refactor while all tests are green, and only then add the new behavior? #### What This Part Should Cover - The red, green, refactor loop, applied visibly at every step - Minimal state at each step, and the exact test that forces each new piece of state - Recognizing when an earlier shortcut has become wrong, and replacing it while the tests stay green - Precise verbal instructions to the person typing, and joint debugging when a test fails unexpectedly ### Part 3 — Expanding the set With the main operations working, discuss how you would expand this set. This part is a verbal discussion; no more code is written. ```hint Use the tests as a safety net Think about what the existing tests already guarantee, and therefore which parts of the class you could change freely without fear. ``` #### Clarifying Questions for this Part - Does "expand" mean supporting more operations, holding many more elements efficiently, or both? #### What This Part Should Cover - Additional operations and the tests that would drive each of them - How the storage would change if complexity started to matter, and why the existing tests make that change safe - Generality and API contracts: a generic element type, iteration, and the equality and hashing rules elements must follow ### What a Strong Answer Covers - Discipline: no behavior added without a failing test that demands it - Test design: edge cases covered by small, well-named, independent tests - Simplicity: resisting premature data structures while noticing when a shortcut has become wrong - Communication: precise instructions to the person typing, predictions before each test run, thinking aloud - Prioritization under time pressure, so that the core operations are covered first ### Follow-up Questions - Once `remove` exists, is a boolean-based `isEmpty()` still correct? Which test tells you, and how do you make sure that test gets written? - If you later switched the storage to a hash table, which of your existing tests should have to change? - How would you test that the set compares elements with `equals` rather than by reference? - An element is mutated after it was added, in a way that changes its equality. What should `contains` return, and how would your implementation behave?

Overview: A test-driven pair-programming exercise in which you describe unit tests while the interviewer types, growing a Java set class one operation at a time with the simplest code that makes each test pass. It tests test-case design, incremental refactoring, clear verbal communication and how you would later expand the set.

Read the full Ode Software Engineer interview experience this question came from
Related Interview Questions

    Implement an HTTP Router That Resolves Handlers for Paths with Named Parameters - Google (medium)
    Review AI-Generated LRU and LFU Cache Changes - Pinterest (medium)
    Debug Colander Output Bugs: Stray None, Nested Lists, and Empty List Versus Null - Stripe (medium)
    Implement an in-memory key-value store with per-key TTL expiration and tests - Netflix (medium)
    Fix a Buggy Spring Boot Movie Search Against Five Search Rules - Amazon (hard)



This screen is a test-driven pair-programming session. You do the thinking and talking; the interviewer does the typing. Together you build a set class in Java one small step at a time: for each set operation you first say which unit tests it needs, the interviewer writes them, and then you direct the smallest change to the class that makes the failing tests pass.

The interviewer's guidance is "do the simplest thing that works". Runtime and memory complexity do not matter in this exercise, but the interviewer will keep challenging you on whether your implementation is really the simplest one that passes the current tests. For example, while isEmpty() is the only behavior under test, it can be implemented with a single boolean; nothing yet requires a data structure that stores elements. Further behavior is added to the class only when a test demands it.

Because the interviewer types, the session is effectively language-agnostic for you: what is assessed is how clearly you express test cases and implementation steps, and how you debug together when a test fails. There is not enough time to implement every operation, so make sure the main ones are covered. The session ends with a verbal discussion of how you would expand the set.
Constraints and Clarifications

    The language is Java and the tests are unit tests; assume JUnit.
    The exact list of operations was not fixed in advance. Assume a minimal set API such as isEmpty() , add(x) , contains(x) , remove(x) and size() , and confirm it with the interviewer.
    Correctness is judged only by the tests written during the session, so any behavior you want must first appear as a test.

Clarifying Questions
Guidance

    Which operations should the set support, and should add and remove return nothing, or a boolean saying whether the set changed, as java.util.Set does?
    What element type should the set hold to start with: a fixed type such as String , or a generic type parameter?
    Is null a legal element? If not, should adding it throw?
    May the class delegate storage to a built-in collection such as ArrayList , or should it manage its own array?
    Should two elements count as the same when they are equals , or only when they are the same object?

Part 1 — Tests first

Choose the order in which you will tackle the operations. For each operation, say which unit test cases you would write, in the order you would write them, and what each one checks. Name each test so that a failure message explains itself.
Hide hint

Order the cases so that every new test fails against the current code for exactly one reason. A test that already passes puts no pressure on the design; a test that fails for three reasons makes the next step too big.
Hide hint

For each operation, think about an element that was never added, the same element added twice, an operation on an empty set, and what one operation does to the results of the others.
What This Part Should Cover
Guidance

    A sensible order of operations, starting from the one that needs the least state
    For each operation, positive cases, negative cases and interactions with the other operations
    Tests that are small, independent and named after the behavior they check
    Edge cases: duplicates, removing an absent element, emptiness after removal, equality of distinct but equal objects

Part 2 — The simplest implementation that passes

Starting from an empty class, direct the interviewer through the changes that make each new test pass. At every step, justify why your change is the simplest one that turns the current failing test green without breaking earlier tests, and say when a refactor is due.
Hide hint

Start with the shortcut the interviewer suggested. Then look for the later test that makes that shortcut give a wrong answer, and decide what the minimal replacement is at that moment.
Clarifying Questions for this Part
Guidance

    When a new test forces a bigger change, may you first refactor while all tests are green, and only then add the new behavior?

What This Part Should Cover
Guidance

    The red, green, refactor loop, applied visibly at every step
    Minimal state at each step, and the exact test that forces each new piece of state
    Recognizing when an earlier shortcut has become wrong, and replacing it while the tests stay green
    Precise verbal instructions to the person typing, and joint debugging when a test fails unexpectedly

Part 3 — Expanding the set

With the main operations working, discuss how you would expand this set. This part is a verbal discussion; no more code is written.
Use the tests as a safety net
Clarifying Questions for this Part
Guidance

    Does "expand" mean supporting more operations, holding many more elements efficiently, or both?

What This Part Should Cover
Guidance

    Additional operations and the tests that would drive each of them
    How the storage would change if complexity started to matter, and why the existing tests make that change safe
    Generality and API contracts: a generic element type, iteration, and the equality and hashing rules elements must follow

What a Strong Answer Covers
Guidance

    Discipline: no behavior added without a failing test that demands it
    Test design: edge cases covered by small, well-named, independent tests
    Simplicity: resisting premature data structures while noticing when a shortcut has become wrong
    Communication: precise instructions to the person typing, predictions before each test run, thinking aloud
    Prioritization under time pressure, so that the core operations are covered first

Follow-up Questions
Guidance

    Once remove exists, is a boolean-based isEmpty() still correct? Which test tells you, and how do you make sure that test gets written?
    If you later switched the storage to a hash table, which of your existing tests should have to change?
    How would you test that the set compares elements with equals rather than by reference?
    An element is mutated after it was added, in a way that changes its equality. What should contains return, and how would your implementation behave?

Browse More Questions
More Software Engineering Fundamentals
•
More Ode
•
More Software Engineer
•
Ode Software Engineer
•
Ode Software Engineering Fundamentals
•
Software Engineer Software Engineering Fundamentals
Write your answer to earn 30 XP

Your first approved answer each day earns 30 XP.

Sign in to write your answer.

Premium members get AI feedback on every answer they post.

Be the first to share your approach

Your insights help other candidates prepare
Ode: Test-Driven Pair Programming: Grow a Java Set Class from Unit Tests

-----
Actually did this with Ode with Anthropic

Simple even if it doesn't make sense. Like boolean for isEmpty and flipping it when add is called. The end implementation was a array with an index into the next open slot