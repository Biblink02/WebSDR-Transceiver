<script lang="ts" setup>
import AppLayout from '&/layouts/AppLayout.vue'

const teamMembers = [
    {
        id: 1,
        name: "Stefan Valentin",
        university: "Darmstadt University of Applied Sciences",
        role: "Team Leader",
        github: "sv-ors",
    },
    {
        id: 2,
        name: "Alberto",
        university: "University of Padua",
        role: "Computer Engineering Student",
        github: "Biblink02"
    },
    {
        id: 3,
        name: "Alexandre",
        university: "University of Télécom Saint-Étienne",
        role: "Computer Engineering Student",
        github: "TheAnacondA57"
    },
    {
        id: 4,
        name: "Clément",
        university: "University of Télécom Saint-Étienne",
        role: "Computer Engineering Student",
        github: "clfusero"
    },
    {
        id: 5,
        name: "Fatemah",
        university: "University of Padua",
        role: "Computer Engineering Student",
        github: "Pitclair"
    },
    {
        id: 6,
        name: "Lorenzo",
        university: "University of Padua",
        role: "Computer Engineering Student",
        github: "Fireentity"
    },
    {
        id: 7,
        name: "Mihir",
        university: "Darmstadt University of Applied Sciences",
        role: "Computer Science Student",
        github: "M1keP1"
    },
    {
        id: 8,
        name: "Vedant",
        university: "Darmstadt University of Applied Sciences",
        role: "Computer Science Student",
        github: "vedant-224"
    }
]

</script>

<template>
    <AppLayout>
        <div class="max-w-7xl mx-auto p-15 font-mono">
            <h1 class="text-5xl font-mono mb-14 text-center select-none text-white">
                Meet Our Team
            </h1>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-12">
                <div
                    v-for="member in teamMembers"
                    :key="member.id"
                    :style="{'--delay': member.id}"
                    class="rounded-lg p-6 flex flex-col items-center text-center motion-safe:animate-fadeIn backdrop-blur-sm"
                    style="animation-delay: calc(var(--delay) * 100ms)"
                >
                    <div class="mb-6">
                        <img
                            :alt="`Photo of ${member.name}`"
                            :src="`https://github.com/${member.github}.png`"
                            class="w-48 h-48 rounded-full object-cover border-4 border-favourite_yellow shadow-md"
                        />
                    </div>

                    <div class="flex items-center gap-2 mb-1">
                        <h2 class="text-2xl font-semibold text-favourite_yellow select-text">
                            {{ member.name }}
                        </h2>
                        <a
                            :aria-label="`Visit ${member.name}'s GitHub profile`"
                            :href="`https://github.com/${member.github}`"
                            class="text-2xl hover:opacity-70 transition-opacity"
                            rel="noopener noreferrer"
                            target="_blank"
                        >
                            🔗
                        </a>
                    </div>

                    <p class="text-white text-sm mb-2 select-text">
                        {{ member.university }}
                    </p>

                    <h3 class="italic text-lg mb-3 text-white select-text">
                        {{ member.role }}
                    </h3>
                </div>
            </div>
        </div>
    </AppLayout>
</template>

<style scoped>
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.motion-safe\:animate-fadeIn {
    animation-name: fadeIn;
    animation-duration: 0.6s;
    animation-fill-mode: both;
    animation-timing-function: ease-in-out;
}

.text-favourite_yellow {
    color: #dbb01f;
}
</style>
