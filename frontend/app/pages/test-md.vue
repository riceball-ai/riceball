<script lang="ts" setup>
definePageMeta({
  layout: false
})
const message = { 
    id: 1,
    message_type: "user",
    content: String.raw`
Test message with **markdown**!
 ` 
}
</script>

<template>
    <Card>
        <CardContent>
            <ChatMessage
                :message=message
            />
        </CardContent>
        
    </Card>
    
</template>