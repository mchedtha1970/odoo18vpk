import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';
import {
  Prompt_400Regular,
  Prompt_500Medium,
  Prompt_600SemiBold,
  Prompt_700Bold,
} from '@expo-google-fonts/prompt';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { HomeScreen } from './src/screens/HomeScreen';
import { JobDetailScreen } from './src/screens/JobDetailScreen';
import { JobsScreen } from './src/screens/JobsScreen';
import { LoginScreen } from './src/screens/LoginScreen';
import { NewRequestScreen } from './src/screens/NewRequestScreen';
import { colors } from './src/theme/colors';
import { fonts } from './src/theme/typography';

export type RootStackParamList = {
  Login: undefined;
  Home: undefined;
  Jobs: { filter?: string; title?: string } | undefined;
  JobDetail: { id: number };
  NewRequest: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function RootNavigator() {
  const { session, loading } = useAuth();
  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg }}>
        <ActivityIndicator size="large" color={colors.brand} />
      </View>
    );
  }
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerTintColor: colors.brand,
        headerTitleStyle: { fontFamily: fonts.semiBold, fontSize: 17, color: colors.ink },
        headerBackTitle: 'กลับ',
        headerBackButtonDisplayMode: 'generic',
      }}
    >
      {session ? (
        <>
          <Stack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Jobs" component={JobsScreen} options={({ route }) => ({ title: route.params?.title || 'ใบงาน' })} />
          <Stack.Screen name="JobDetail" component={JobDetailScreen} options={{ title: 'รายละเอียด' }} />
          <Stack.Screen name="NewRequest" component={NewRequestScreen} options={{ title: 'แจ้งซ่อม' }} />
        </>
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  const [fontsLoaded] = useFonts({
    Prompt_400Regular,
    Prompt_500Medium,
    Prompt_600SemiBold,
    Prompt_700Bold,
  });
  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg }}>
        <ActivityIndicator size="large" color={colors.brand} />
      </View>
    );
  }
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer>
          <StatusBar style="dark" />
          <RootNavigator />
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
